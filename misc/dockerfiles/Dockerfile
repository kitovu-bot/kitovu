FROM python:3.6.4-alpine3.6

WORKDIR /opt/project

RUN apk --no-cache add alpine-sdk libffi-dev openssl-dev

RUN pip install tox

ARG UID
ARG GID

RUN addgroup -g $GID local-group && \
    adduser -D -u $UID -G local-group local-user

COPY entrypoint.sh /opt/bin/entrypoint.sh
RUN chmod +x /opt/bin/entrypoint.sh

USER local-user

RUN pip install -r requirements.txt -r requirements-dev.txt

ENTRYPOINT ["/opt/bin/entrypoint.sh"]

CMD ["python"]
