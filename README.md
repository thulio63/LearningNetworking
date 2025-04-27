# My First Python Server

## Purpose

This is a project that explores networking concepts through sockets in Python. The code is based on a [tutorial from Real Python](https://realpython.com/python-sockets/) that I am slowly expanding to improve functionality and my own understanding of the concepts.

## Usage

There are currently two files that run for each version of the application. The relevant two files are _babysFirstAppServer_ and _babysFirstAppClient_ and these are the only two I am actively iterating on. There are other previous versions in the repo, but those are more for reference to simpler versions of the same concepts.

For the server side application, run the following:
`Python babysFirstAppServer.py <IP Address> <Port>`

On the client side application, run the following:
`Python babysFirstAppClient.py <IP Address> <Port> <Action> <Value>`
Currently the only functional actions are **search** and **message**.
