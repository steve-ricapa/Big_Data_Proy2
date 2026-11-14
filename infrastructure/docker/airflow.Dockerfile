FROM apache/airflow:2.11.0-python3.11
RUN mkdir -p /opt/airflow/checkpoints
RUN pip install --no-cache-dir --constraint https://raw.githubusercontent.com/apache/airflow/constraints-2.11.0/constraints-3.11.txt ijson pymongo cassandra-driver neo4j pydantic-settings
COPY --chown=airflow:root src/ /opt/project/src/
ENV PYTHONPATH=/opt/project/src
