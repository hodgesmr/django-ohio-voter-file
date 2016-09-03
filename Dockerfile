FROM python:3.5
RUN apt-get update -y
RUN apt-get upgrade -y
RUN apt-get install postgresql postgresql-client -y
ENV APP_DIR=/opt/ohiovoter \
    PYTHONUNBUFFERED=1
RUN pip install -U pip ipython
RUN mkdir -p $APP_DIR
WORKDIR $APP_DIR
ADD setup.py requirements.txt README.md $APP_DIR/
ADD ohiovoter/__init__.py $APP_DIR/ohiovoter/
RUN pip install -r requirements.txt
RUN pip uninstall django-ohio-voter-file -y
ADD . $APP_DIR/
