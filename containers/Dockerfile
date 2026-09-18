FROM python:3.13-slim
WORKDIR /opt/cdrse
COPY . .
RUN python -m pip install --no-cache-dir .
ENTRYPOINT ["cdrse"]
CMD ["self-check", "--json"]
