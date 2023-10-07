FROM python:3.11.6-alpine3.18
RUN cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo 'Asia/Shanghai' > /etc/timezone
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.ustc.edu.cn/g' /etc/apk/repositories \
      && apk add --no-cache --virtual build-dependencies\
            build-base \
            gcc \
            musl-dev \
            libc-dev \
            libffi-dev \
            mariadb-dev \
            libxslt-dev \
            libpq-dev \
            libstdc++ \
      && pip3 install pip install aio-scrapy[all] -U -i https://mirrors.aliyun.com/pypi/simple \
      && rm -rf .cache/pip3 \
      && apk del build-dependencies
CMD ["aioscrapy", "version"]
