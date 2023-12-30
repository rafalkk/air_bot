FROM python:3-alpine

ENV TELEGRAM_BOT_API_KEY=

WORKDIR /APP

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

RUN adduser --disabled-password --gecos "" appuser && chown appuser .

USER appuser

CMD [ "python", "./bot.py" ]