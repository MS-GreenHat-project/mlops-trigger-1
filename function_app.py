import azure.functions as func
import datetime
import json
import logging
import os
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
import requests

app = func.FunctionApp()

# 환경변수 로딩 함수
def get_env(key: str, default=None):
    return os.environ.get(key, default)

# Blob Storage에서 이미지 개수 체크 함수 (구현 예정)
def count_images_in_blob(account_name, container_name, prefix):
    # 환경변수에서 SAS 토큰 또는 연결 문자열 우선 사용
    conn_str = get_env('AzureWebJobsStorage')
    if conn_str:
        blob_service_client = BlobServiceClient.from_connection_string(conn_str)
    else:
        credential = DefaultAzureCredential()
        blob_service_client = BlobServiceClient(
            f"https://{account_name}.blob.core.windows.net", credential=credential)

    container_client = blob_service_client.get_container_client(container_name)
    count = 0
    blobs = container_client.list_blobs(name_starts_with=prefix)
    for blob in blobs:
        # 이미지 파일만 카운트 (jpg, jpeg, png, bmp, gif 등)
        if blob.name.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".gif")):
            count += 1
    return count

# Discord Webhook 알림 함수 (구현 예정)
def send_discord_alert(webhook_url, message):
    data = {
        "content": message
    }
    response = requests.post(webhook_url, json=data)
    if response.status_code != 204:
        raise Exception(f"Discord Webhook 전송 실패: {response.status_code}, {response.text}")

@app.timer_trigger(schedule="0 0 */5 * * *", arg_name="myTimer", run_on_startup=False,
              use_monitor=False) 
def BlobChecker(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function executed.')

    account_name = get_env('BLOB_ACCOUNT_NAME')
    container_name = get_env('BLOB_CONTAINER_NAME')
    webhook_url = get_env('DISCORD_WEBHOOK_URL')
    labeling_url = get_env('LABELING_TOOL_URL')
    prefix = 'raw/'

    if not all([account_name, container_name, webhook_url, labeling_url]):
        logging.error('필수 환경변수(BLOB_ACCOUNT_NAME, BLOB_CONTAINER_NAME, DISCORD_WEBHOOK_URL, LABELING_TOOL_URL)가 누락되었습니다.')
        return

    try:
        count = count_images_in_blob(account_name, container_name, prefix)
        logging.warning(f'raw/ 내 이미지 개수: {count}')
        if count > 500:
            message = (
                f"🚨 이미지가 {count}개나 쌓였습니다! 🚨\n"
                f"라벨링 요정이 울고 있어요 😭\n"
                f"어서 라벨링 작업을 진행하고 export 해주세요!\n"
                f"[🖼️ 라벨링 작업 바로가기]({labeling_url})\n"
                f"(이 메시지를 무시하면... 이미지가 더 쌓일지도? 🤖)"
            )
            send_discord_alert(webhook_url, message)
            logging.warning('Discord 알림 전송 완료')
    except Exception as e:
        logging.error(f'오류 발생: {e}')