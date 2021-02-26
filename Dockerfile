FROM python:3.7.4

RUN mkdir -p /home/hypgen
WORKDIR /home/hypgen

RUN pip install --upgrade pip

ADD requirements.txt .
RUN pip install -r requirements.txt
RUN pip install gunicorn
RUN python -m spacy download en

ADD app app
ADD boot.sh ./
RUN chmod +x boot.sh

ENV FLASK_APP hyp_gen.py

EXPOSE 8099
ENTRYPOINT ["./boot.sh"]