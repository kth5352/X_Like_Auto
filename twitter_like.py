import tkinter as tk
from tkinter import messagebox
import tweepy
import json
import pandas as pd
from cryptography.fernet import Fernet, InvalidToken
from datetime import datetime
from dotenv import load_dotenv
import os
import base64

load_dotenv()

API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.getenv('ACCESS_TOKEN_SECRET')
BEARER_TOKEN = os.getenv('BEARER_TOKEN')

# 고정된 암호화 키를 사용하도록 설정
encryption_key = os.getenv('ENCRYPTION_KEY')

# 고정된 암호화 키가 없거나 올바르지 않으면 새로 생성하고 저장합니다.
def get_or_create_encryption_key():
    if encryption_key is None or len(encryption_key.encode()) != 44:
        new_key = Fernet.generate_key()
        with open('.env', 'a') as f:
            f.write(f'\nENCRYPTION_KEY={new_key.decode()}')
        return new_key
    return encryption_key.encode()

ENCRYPTION_KEY = get_or_create_encryption_key()

# 암호화 및 복호화 함수
def encrypt(data, key):
    f = Fernet(key)
    return f.encrypt(data.encode())

def decrypt(data, key):
    f = Fernet(key)
    try:
        return f.decrypt(data).decode()
    except InvalidToken:
        messagebox.showerror("에러", "암호화 키가 일치하지 않습니다. 복호화에 실패했습니다.")
        return None

# Twitter API 인증
try:
    client = tweepy.Client(bearer_token=BEARER_TOKEN, consumer_key=API_KEY, consumer_secret=API_SECRET,
                           access_token=ACCESS_TOKEN, access_token_secret=ACCESS_TOKEN_SECRET)
except Exception as e:
    messagebox.showerror("에러", f"Twitter API 인증에 실패했습니다: {e}")

# 데이터 저장용 DataFrame 초기화
data = []

# 게시물에 좋아요를 누르고 기록하는 함수
def like_and_record(tweet):
    try:
        client.create_favorite(tweet.id)
        record = {
            'url': f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}",
            'author': tweet.user.screen_name,
            'time': tweet.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'status': '좋아요'
        }
        data.append(record)
        update_log(f"{tweet.user.screen_name}님의 트윗에 좋아요를 눌렀습니다: {tweet.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n{tweet.text}\n")
    except Exception as e:
        record = {
            'url': f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}",
            'author': tweet.user.screen_name,
            'time': tweet.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'status': '좋아요 실패'
        }
        data.append(record)
        update_log(f"{tweet.user.screen_name}님의 트윗에 좋아요를 누르지 못했습니다: {tweet.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n{tweet.text}\n")

# 데이터 저장 함수
def save_data():
    try:
        df = pd.DataFrame(data)
        df.to_csv('like_records.csv', index=False)
    except Exception as e:
        messagebox.showerror("에러", f"데이터 저장에 실패했습니다: {e}")

# 스트리밍 리스너 클래스 정의
class MyStreamListener(tweepy.StreamingClient):
    def on_tweet(self, tweet):
        like_and_record(tweet)
        save_data()

    def on_error(self, status_code):
        if status_code == 420:
            # Rate limit error
            return False
        else:
            messagebox.showerror("에러", f"스트리밍 에러: {status_code}")

# 스트리밍 함수
def start_stream(user_id):
    try:
        myStreamListener = MyStreamListener(BEARER_TOKEN)
        myStreamListener.add_rules(tweepy.StreamRule(f"from:{user_id}"))
        myStreamListener.filter()
    except Exception as e:
        messagebox.showerror("에러", f"스트리밍 시작에 실패했습니다: {e}")

# 계정 정보 암호화 및 저장
def save_credentials(username, password):
    try:
        encrypted_username = encrypt(username, ENCRYPTION_KEY)
        encrypted_password = encrypt(password, ENCRYPTION_KEY)
        with open('credentials.json', 'w') as f:
            json.dump({
                'username': encrypted_username.decode(),
                'password': encrypted_password.decode()
            }, f)
    except Exception as e:
        messagebox.showerror("에러", f"계정 정보 저장에 실패했습니다: {e}")

# 계정 정보 복호화 및 불러오기
def load_credentials():
    try:
        with open('credentials.json', 'r') as f:
            credentials = json.load(f)
        username = decrypt(credentials['username'], ENCRYPTION_KEY)
        password = decrypt(credentials['password'], ENCRYPTION_KEY)
        if username is None or password is None:
            raise ValueError("복호화에 실패했습니다.")
        return username, password
    except FileNotFoundError:
        messagebox.showwarning("경고", "저장된 계정 정보가 없습니다.")
        return None, None
    except Exception as e:
        messagebox.showerror("에러", f"계정 정보 불러오기에 실패했습니다: {e}")
        return None, None

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
        try:
            user = client.get_user(username=username, user_auth=True)
            start_stream(user.data.id)  # 로그인 후 스트리밍 시작
        except tweepy.TweepyException as e:
            messagebox.showerror("에러", f"사용자 정보를 가져오는데 실패했습니다: {e}")
    else:
        messagebox.showwarning("경고", "아이디와 비밀번호를 모두 입력해주세요.")

# 계정 불러오기 버튼 클릭 이벤트 처리 함수
def on_load():
    username, password = load_credentials()
    if username and password:
        username_entry.delete(0, tk.END)
        username_entry.insert(0, username)
        password_entry.delete(0, tk.END)
        password_entry.insert(0, password)
        messagebox.showinfo("정보", "계정 정보가 성공적으로 불러와졌습니다!")
        try:
            user = client.get_user(username=username, user_auth=True)
            start_stream(user.data.id)  # 불러온 후 스트리밍 시작
        except tweepy.TweepyException as e:
            messagebox.showerror("에러", f"사용자 정보를 가져오는데 실패했습니다: {e}")

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
login_button.grid(row=2, column=0, pady=10)

load_button = tk.Button(frame, text="계정 불러오기", command=on_load)
load_button.grid(row=2, column=1, pady=10)

log_frame = tk.Frame(app)
log_frame.pack(pady=10)

log_text = tk.Text(log_frame, wrap='word', height=15, width=50)
log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

scrollbar = tk.Scrollbar(log_frame, command=log_text.yview)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

log_text.config(yscrollcommand=scrollbar.set)

app.mainloop()
