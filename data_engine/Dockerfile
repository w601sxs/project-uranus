FROM python:3.8-slim AS builder

LABEL maintainer="ruyyi0323@gmail.com"
LABEL version="v0.1"
LABEL python_version="3.8"

# Set some environment variables. PYTHONUNBUFFERED keeps Python from buffering our standard
# output stream, which means that logs can be delivered to the user quickly. PYTHONDONTWRITEBYTECODE
# keeps Python from writing the .pyc files which are unnecessary in this case. We also update
# PATH so that the train and serve programs are found when the container is invoked.

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

RUN apt-get clean && \
    apt-get update -y && \
    apt-get install -y --no-install-recommends \
    build-essential ca-certificates curl wget nginx tree ffmpeg

# echo ffmpeg version
RUN echo ffmpeg -version

# install necessary packages 
COPY requirements.txt .
RUN pip install -r requirements.txt

RUN mkdir -p "/data/stream_info"
RUN mkdir -p "/data/raw_audio"
RUN mkdir -p "/data/processed_audio"
RUN mkdir -p "/data/manifests"
RUN chmod -R +x "/data/"

FROM builder

COPY code "/code"
RUN chmod -R +x "/code/"

