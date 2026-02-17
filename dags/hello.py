from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'sotabinda.com',
    'start_date': datetime(2024, 1, 25),
    'catchup': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}

dag = DAG(
    'hello_world',
    default_args=default_args,
    schedule=timedelta(days=1),
    description='Simple hello world DAG to test Airflow is working',
)

t1 = BashOperator(
    task_id='hello_world',
    bash_command='echo "Hello World" && date',
    dag=dag,
)

t2 = BashOperator(
    task_id='hello_dml',
    bash_command='echo "Hello Data Mastery Lab" && date',
    dag=dag,
)

t1 >> t2