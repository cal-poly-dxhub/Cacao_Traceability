import pymysql
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)
#SECRET_NAME = 'Aurora'

def get_secret(secret_name):
    client = boto3.client("secretsmanager")

    response = client.get_secret_value(
        SecretId=secret_name
    )
    
    return response.get('SecretString')

    import json

def recordNextVisit(contact_number, type_of_visit, visit_time):
    print(contact_number, " ", type_of_visit, " ", visit_time)
    # try:
    #     db_credentials = eval(get_secret(SECRET_NAME))
    # except Exception as e:
    #     logger.error(e)
    #     logger.error("could not obtain secret")

    try:
        conn = pymysql.connect(
            host="cacao-db.cpzzbnizneyx.us-west-2.rds.amazonaws.com",
            user="admin",
            password="",
            database="Cacao",
            connect_timeout=5
        )
        cur = conn.cursor()
        sql = "INSERT INTO ScheduleVisit(FarmerCell, VisitDate, VistPurpose) VALUES(%s, %s, %s)"
        logger.debug('SQL={}'.format(sql))
        logger.debug('ARGS={}'.format(contact_number, visit_time, type_of_visit))
        cur.execute(sql, (contact_number, visit_time, type_of_visit))
        conn.commit()
        conn.close()

    except Exception as e:
        print("Error reading data from MySQL table", e)

def getMarketPriceDB():
    price = "0"
    try:
        conn = pymysql.connect(
            host="cacao-db.cpzzbnizneyx.us-west-2.rds.amazonaws.com",
            user="admin",
            password="",
            database="Cacao",
            connect_timeout=5
        )
        cur = conn.cursor()
        sql = "SELECT market_price from Price p Order by price_date DESC limit 1"
        logger.debug('SQL={}'.format(sql))
        cur.execute(sql)


        records = cur.fetchall()
        print("Total number of rows in table: ", cur.rowcount)

        print("\nPrinting each row")
        for row in records:
            price = row[0]
        conn.close()
    except Exception as e:
        print("Error reading data from MySQL table", e)
    
    return price





