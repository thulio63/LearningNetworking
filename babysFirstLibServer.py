import io
import json
import selectors
import struct
import sys

request_search = {
    "timmy": "hi! i'm scared of bumblebees...",
    "jason": "my name is quite unfortunate. i've never even been to a summer camp!",
    "stack": "so here's how you eat pussy"
}


class Message:
    def __init__(self, selector, sock, addr):
        self.selector = selector
        self.sock = sock
        self.addr = addr
        self._recv_buffer = b""
        self._send_buffer = b""
        self._jsonheader_len = None
        self.jsonheader = None
        self.request = None
        self.response_created = False
        
    def _set_selector_events_mask(self, mode):
        """Set selector to listen for events in modes 'r', 'w', and 'rw'"""
        if mode == "r":
            events = selectors.EVENT_READ
        elif mode == "w":
            events = selectors.EVENT_WRITE
        elif mode == "rw":
            events = selectors.EVENT_READ | selectors.EVENT_WRITE
        else:
            raise ValueError(f"Invalid events mask mode: {mode!r}")
        self.selector.modify(self.sock, events, data=self)
        
    def _read(self):
        try:
            data = self.sock.recv(4096) # ready to read
        except BlockingIOError:
            pass # temp unavailable resource
        else:
            if data:
                self._recv_buffer += data
            else:
                raise RuntimeError("Peer closed.")
        
    def _write(self):
        if self._send_buffer:
            print(f"Sending {self._send_buffer!r} to {self.addr}")
            try:
                sent = self.sock.send(self._send_buffer) # ready to write
            except BlockingIOError:
                pass # temp unavailable resource
            else:
                self._send_buffer = self._send_buffer[sent:]
                if sent and not self._send_buffer:
                    self.close() # closes when buffer drained, response is sent
                    
    def _json_encode(self, obj, encoding):
        return json.dumps(obj, ensure_ascii=False).encode(encoding)
    
    def _json_decode(self, json_bytes, encoding):
        tiow = io.TextIOWrapper(
            io.BytesIO(json_bytes), encoding=encoding, newline=""
        )
        obj = json.load(tiow)
        tiow.close()
        return obj
    
    def _create_message(
        self, *, content_bytes, content_type, content_encoding
    ):
        jsonheader = {
            "byteorder": sys.byteorder,
            "content-type": content_type,
            "content-encoding": content_encoding,
            "content-length": len(content_bytes),
        }
        jsonheader_bytes = self._json_encode(jsonheader, "utf-8")
        message_hdr = struct.pack(">H", len(jsonheader_bytes))
        message = message_hdr + jsonheader_bytes + content_bytes
        return message
    
    def _create_response_json_content(self):
        action = self.request.get("action")
        # add actions here to build functionality
        if action == "search":
            query = self.request.get("value")
            answer = request_search.get(query) or f"No match for '{query}'"
            content = {"result": answer}
        elif action == "message":
            print(f"User message: {self.request.get("value")}")
            answer = input("Input your response:\n")
            content = {"result": answer}
        else:
            content = {"result": f"Error: invalid action '{action}'"}
        content_encoding = "utf-8"
        response = {
            "content_bytes": self._json_encode(content, content_encoding),
            "content_type": "text/json",
            "content_encoding": content_encoding,
        }
        return response
    
    def _create_response_binary_content(self):
        response = {
            "content_bytes": b"First 10 bytes of request: " 
            + self.request[:10],
            "content_type": "binary/custom-server-binary-type",
            "content_encoding": "binary",
        }
        return response
    
    
    def process_events(self, mask):
        if mask & selectors.EVENT_READ:
            self.read()
        if mask & selectors.EVENT_WRITE:
            self.write()
            
    def read(self):
        self._read()
        
        if self._jsonheader_len is None:
            self.process_protoheader()
            
        if self._jsonheader_len is not None:
            if self.jsonheader is None:
                self.process_jsonheader()
                
        if self.jsonheader:
            if self.request is None:
                self.process_request()
                
    def write(self):
        if self.request:
            if not self.response_created:
                self.create_response()
            
            self._write()
            
    def close(self):
        print(f"Closing connection to {self.addr}")
        try:
            self.selector.unregister(self.sock)
        except Exception as e:
            print(
                f"Error: selector.unregister() exception for "
                f"{self.addr}: {e!r}"
            )
        
        try:
            self.sock.close()
        except OSError as e:
            print(f"Error: socket.close() exception for {self.addr}: {e!r}")
        finally:
            self.sock = None # remove ref to socket obj for garbage collection
        
    def process_protoheader(self):
        hdrlen = 2
        if len(self._recv_buffer) >= hdrlen:
            self._jsonheader_len = struct.unpack(
                ">H", self._recv_buffer[:hdrlen]
            )[0]
            self._recv_buffer = self._recv_buffer[hdrlen:]
            
    def process_jsonheader(self):
        hdrlen = self._jsonheader_len
        if len(self._recv_buffer) >= hdrlen:
            self.jsonheader = self._json_decode(
                self._recv_buffer[:hdrlen], "utf-8"
            )
            self._recv_buffer = self._recv_buffer[hdrlen:]
            for reqhdr in (
                "byteorder",
                "content-length",
                "content-type",
                "content-encoding",
            ):
                if reqhdr not in self.jsonheader:
                    raise ValueError(f"Missing required header '{reqhdr}'")
                
    def process_request(self):
        content_len = self.jsonheader["content-length"]
        if not len(self._recv_buffer) >= content_len:
            return
        data = self._recv_buffer[:content_len]
        self._recv_buffer = self._recv_buffer[content_len:]
        if self.jsonheader["content-type"] == "text/json":
            encoding = self.jsonheader["content-encoding"]
            self.request = self._json_decode(data, encoding)
            print(f"Received request {self.request!r} from {self.addr}")
        else:
            self.request = data # binary or unknown content-type
            print(
                f"Received {self.jsonheader['content-type']} "
                f"request from {self.addr}"
            )
        # done reading, start writing
        self._set_selector_events_mask("w")
        
    def create_response(self):
        if self.jsonheader["content-type"] == "text/json":
            response = self._create_response_json_content()
        else:
            response = self._create_response_binary_content()
        message = self._create_message(**response)
        self.response_created = True
        self._send_buffer += message