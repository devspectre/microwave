# Microwave
## _The Ultimate cooking experience, Ever_

## Summary

This is purely for demonstration purpose, thus it does not support any production deployment.
You can run/test it on your local machine.

## Features

- Adjust power(percentage)
- Adjust counter(seconds)
- Cancel microwave operation(requires JWT)

## Installation

- [docker](https://docs.docker.com/engine/install/)
- [docker-compose](https://docs.docker.com/compose/install/)

## Run

### Backend

Copy `.env.example` and fill out the values.

Run the following command
```sh
make build
# if your os does not support makefile
docker-compose build
```

```sh
make run
# if your os does not support makefile
docker-compose up
```

### Front-end

Visit the following URL on your browser.
`http://0.0.0.0:8000/static/index.html`


## Developer Note

Due to lack of time, no unit tests are added.
Better to have them in place.

Can use slim-buster image to optimize docker image size.