# "FROM" starts us out from this Ubuntu-based image
# https://github.com/tiangolo/uwsgi-nginx-flask-docker/blob/master/python3.7/Dockerfile

FROM tiangolo/meinheld-gunicorn-flask:python3.8

# Update to the latest PIP
RUN pip3 install --upgrade pip

# Our application code will exist in the /app directory,
# so set the current working directory to that
WORKDIR /app

COPY ./requirements.txt /app

# install our dependencies
RUN  pip3 install -r requirements.txt

# Copy our files into the current working directory WORKDIR
COPY ./ /app

# Make /app/* available to be imported by Python globally to better support several
# use cases like Alembic migrations.
ENV PYTHONPATH=/app
