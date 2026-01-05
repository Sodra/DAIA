FROM alpine:3.19

RUN apk add --no-cache bash git curl docker-cli docker-cli-compose

WORKDIR /repo

CMD ["bash", "/repo/scripts/update.sh"]
