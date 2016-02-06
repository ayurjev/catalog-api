FROM ubuntu:14.04

RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

RUN apt-get update
RUN apt-get install -y \
    build-essential wget git libcurl4-gnutls-dev libexpat1-dev gettext libz-dev libssl-dev \
    libjpeg62-dev zlib1g-dev libfreetype6-dev liblcms1-dev && \
    apt-get clean

RUN wget https://www.python.org/ftp/python/3.5.1/Python-3.5.1.tgz && tar zxf Python-3.5.1.tgz && \
    cd Python-3.5.1 && ./configure && make && make install && rm -rf Python-3.5.1 && rm -f Python-3.5.1.tgz

RUN wget http://dev.mysql.com/get/Downloads/Connector-Python/mysql-connector-python-2.1.3.tar.gz && \
    tar xf mysql-connector-python-2.1.3.tar.gz && cd mysql-connector-python-2.1.3 && python3 setup.py install && \
    rm -rf mysql-connector-python-2.1.3 && rm -f mysql-connector-python-2.1.3.tar.gz

RUN pip3 install git+https://git@github.com/ayurjev/envi.git#egg=envi && \
    pip3 install git+https://git@github.com/ayurjev/suit.git#egg=suit && \
    pip3 install git+https://git@github.com/ayurjev/mapex.git#egg=mapex && \
    pip3 install uwsgi webtest requests pymongo

RUN echo '#!/bin/bash' >> /usr/local/bin/runtests && \
    echo 'python3 -m unittest discover /var/www/' >> /usr/local/bin/runtests && \
    chmod a+x /usr/local/bin/runtests

WORKDIR /var/www/
COPY . /var/www/

EXPOSE 80
ENTRYPOINT ["uwsgi"]
CMD ["--http", ":80", "--wsgi-file", "application.py"]