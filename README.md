# Demos

## requirements

Install requirements to run these demos:

```sh
$ pip install -r requirements.txt
```

## named.py:

One shared terminal per URL endpoint

Plus a /new URL which will create a new terminal and redirect to it.

## single.py:

A single common terminal for all websockets.

## unique.py:

A separate terminal for every websocket opened.

### worker env

[env](https://github.com/judge0/api-base)

there is a sample docker image

```
docker push atchen1988/juage-api:tagname
```
