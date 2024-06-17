import tkinter as tk
from tkinter import messagebox
import tweepy
import json
import pandas as pd
from cryptography.fernet import Fernet
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.getenv('ACCESS_TOKEN_SECRET')
BEARER_TOKEN = os.getenv('BEARER_TOKEN')
ENCRYPTION_KEY = Fernet.generate_key()

# 암호화 및 복호화 함수
def encrypt(data, key):
    f = Fernet(key)
    return f.encrypt(data.encode())

def decrypt(data, key):
    f = Fernet(key)
    return f.decrypt(data).decode()

# Twitter API 인증
client = tweepy.Client(bearer_token=BEARER_TOKEN, consumer_key=API_KEY, consumer_secret=API_SECRET, access_token=ACCESS_TOKEN, access_token_secret=ACCESS_TOKEN_SECRET)

# 데이터 저장용 DataFrame 초기화
data = []

# 게시물에 좋아요를 누르고 기록하는 함수
def like_and_record(tweet_id, username, text, created_at):
    try:
        client.like(tweet_id)
        record = {
            'url': f"https://twitter.com/{username}/status/{tweet_id}",
            'author': username,
            'time': created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'status': '좋아요'
        }
        data.append(record)
        update_log(f"{username}님의 트윗에 좋아요를 눌렀습니다: {created_at.strftime('%Y-%m-%d %H:%M:%S')}\n{text}\n")
    except Exception as e:
        record = {
            'url': f"https://twitter.com/{username}/status/{tweet_id}",
            'author': username,
            'time': created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'status': '좋아요 실패'
        }
        data.append(record)
        update_log(f"{username}님의 트윗에 좋아요를 누르지 못했습니다: {created_at.strftime('%Y-%m-%d %H:%M:%S')}\n{text}\n")

# 데이터 저장 함수
def save_data():
    df = pd.DataFrame(data)
    df.to_csv('like_records.csv', index=False)

# 스트리밍 리스너 클래스 정의
class MyStreamListener(tweepy.StreamingClient):
    def on_tweet(self, tweet):
        like_and_record(tweet.id, tweet.author_id, tweet.text, tweet.created_at)
        save_data()

    def on_error(self, status_code):
        if status_code == 420:
            # Rate limit error
            return False

# 스트리밍 함수
def start_stream(user_id):
    myStreamListener = MyStreamListener(BEARER_TOKEN)
    myStreamListener.add_rules(tweepy.StreamRule(f"from:{user_id}"))
    myStreamListener.filter()

# 계정 정보 암호화 및 저장
def save_credentials(username, password):
    encrypted_username = encrypt(username, ENCRYPTION_KEY)
    encrypted_password = encrypt(password, ENCRYPTION_KEY)
    with open('credentials.json', 'w') as f:
        json.dump({
            'username': encrypted_username.decode(),
            'password': encrypted_password.decode()
        }, f)

# 계정 정보 복호화 및 불러오기
def load_credentials():
    with open('credentials.json', 'r') as f:
        credentials = json.load(f)
    username = decrypt(credentials['username'], ENCRYPTION_KEY)
    password = decrypt(credentials['password'], ENCRYPTION_KEY)
    return username, password

# 로그 업데이트 함수
def update_log(message):
    log_text.insert(tk.END, message)
    log_text.yview(tk.END)

# 로그인 버튼 클릭 이벤트 처리 함수
def on_login():
    username = username_entry.get()
    password = password_entry.get()
    if username and password:
        save_credentials(username, password)
        messagebox.showinfo("정보", "계정 정보가 성공적으로 저장되었습니다!")
        user = client.get_user(username=username)
        start_stream(user.data.id)  # 로그인 후 스트리밍 시작
    else:
        messagebox.showwarning("경고", "아이디와 비밀번호를 모두 입력해주세요.")

# GUI 설정
app = tk.Tk()
app.title("트위터 자동 좋아요 봇")

frame = tk.Frame(app)
frame.pack(pady=20)

tk.Label(frame, text="트위터 아이디:").grid(row=0, column=0, padx=5, pady=5)
username_entry = tk.Entry(frame)
username_entry.grid(row=0, column=1, padx=5, pady=5)

tk.Label(frame, text="비밀번호:").grid(row=1, column=0, padx=5, pady=5)
password_entry = tk.Entry(frame, show="*")
password_entry.grid(row=1, column=1, padx=5, pady=5)

login_button = tk.Button(frame, text="로그인 정보 저장", command=on_login)
login_button.grid(row=2, columnspan=2, pady=10)

log_frame = tk.Frame(app)
log_frame.pack(pady=10)

log_text = tk.Text(log_frame, wrap='word', height=15, width=50)
log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

scrollbar = tk.Scrollbar(log_frame, command=log_text.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

log_text.config(yscrollcommand=scrollbar.set)

app.mainloop()
