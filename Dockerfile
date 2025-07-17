FROM nginx:alpine

#Python installieren
RUN apk add --no-cache python3 py3-pip \
    && pip3 install --break-system-packages requests pandas

COPY . /usr/share/nginx/html

COPY datawrapper.py /datawrapper.py
# startup script kopieren
COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 80

VOLUME ["/data"]

ENTRYPOINT ["/start.sh"]