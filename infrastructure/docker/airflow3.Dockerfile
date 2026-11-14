# Migration candidate kept separate from the verified Airflow 2 baseline.
FROM apache/airflow:slim-3.4.0-python3.11
COPY --chown=airflow:root airflow/requirements.lock /opt/project/airflow-requirements.lock
RUN pip install --no-cache-dir --require-hashes -r /opt/project/airflow-requirements.lock && pip check
RUN mkdir -p /opt/airflow/checkpoints /opt/airflow/auth
COPY --chown=airflow:root src/ /opt/project/src/
ENV PYTHONPATH=/opt/project/src
