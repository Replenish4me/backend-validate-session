import boto3
import json
import pymysql
import datetime
import os

def lambda_handler(event, context):
    
    # Leitura do token de sessão da requisição
    token = event['token']
    
    # Conexão com o banco de dados
    secretsmanager = boto3.client('secretsmanager')
    response = secretsmanager.get_secret_value(SecretId=f'replenish4me-db-password-{os.environ.get("env", "dev")}')
    db_password = response['SecretString']
    rds = boto3.client('rds')
    response = rds.describe_db_instances(DBInstanceIdentifier=f'replenish4medatabase{os.environ.get("env", "dev")}')
    endpoint = response['DBInstances'][0]['Endpoint']['Address']
    # Conexão com o banco de dados
    with pymysql.connect(
        host=endpoint,
        user='admin',
        password=db_password,
        database='replenish4me'
    ) as conn:
    
        # Verificação da sessão ativa no banco de dados
        with conn.cursor() as cursor:
            sql = "SELECT usuario_id, ultima_atividade FROM SessoesAtivas WHERE id = %s"
            cursor.execute(sql, (token,))
            result = cursor.fetchone()
            
            if result is None:
                response = {
                    "statusCode": 401,
                    "body": json.dumps({"message": "Sessão inválida"})
                }
                return response
            
            usuario_id, ultima_atividade = result
            
            # Verificação do tempo da última atividade da sessão
            tempo_maximo_inatividade = 60 * 60 * 4  # 4 horas
            if (datetime.datetime.now() - ultima_atividade).seconds > tempo_maximo_inatividade:
                # Sessão expirada
                sql = "DELETE FROM SessoesAtivas WHERE id = %s"
                cursor.execute(sql, (token,))
                conn.commit()
                response = {
                    "statusCode": 401,
                    "body": json.dumps({"message": "Sessão expirada"})
                }
                return response
            
            # Atualização da última atividade da sessão
            sql = "UPDATE SessoesAtivas SET ultima_atividade = %s WHERE id = %s"
            cursor.execute(sql, (datetime.datetime.now(), token))
            conn.commit()

    # Retorno da resposta da função
    response = {
        "statusCode": 200,
        "body": json.dumps({"usuario_id": usuario_id})
    }
    return response
