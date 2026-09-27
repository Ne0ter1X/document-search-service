FROM ubuntu:latest
LABEL authors="deckfly"

ENTRYPOINT ["top", "-b"]