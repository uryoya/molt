# Molt
[POOL](https://github.com/mookjp/pool)クローンです。

## セットアップ
### 依存しているもの
* python3.5
* pip (パッケージインストール用)
* docker
* docker-compose

### セットアップ手順
1. リポジトリを任意のディレクトリに置いて、リポジトリ内に入る
```
$ git clone https://github.com/uryoya/molt.git ~/
$ cd ~/molt
```
2. venvの構築(開発/テスト環境用)
```
$ python3.5 -m venv venv
$ source venv/bin/activate
```
3. pythonパッケージのインストール
```
$ pip install -r requirement.txt
```
4. config/molt_app.cfgの設定
```
$ cp config/molt_app.cfg.sample config/molt_app.cfg
$ vim config/molt_app.cfg    # 好みのエディタで
```
config/molt.app.cfg内(:memo:は任意の設定にしてください。:warning:はデフォルトの設定を推奨します。)

|設定名|既定値|:question:|説明|
|:----|:----|:---|:---|
|DEBUG|True|:memo:|Flaskのデバッグモード。運用時はFalseに。|
|TESTING|False|:memo:|Flaskのテストモード。同上。|
|HOST|0.0.0.0|:warning:|MoltのIP|
|PORT|5000|:warning:|MoltのPort|
|REDIS_HOST|localhost|:warning:|Redis(Dockerイメージを起動します)のIP。|
|REDIS_PORT|6379|:warning:|RedisのPort|
|BASE_DOMAIN|127.0.0.1.xip.io|:memo:|ドメイン|
|GITHUB_TOKEN||:memo:|WebHook用のパーソナルアクセストークン|

5. リバースプロキシの準備
```
$ docker rmi unblee/mirror:latest
```

6. 起動
```
$ python molt_app.py  # バックグラウンドで起動する場合は nohup を先頭に、 & を末尾に付ける。
$ docker-compose up -d
```

### その他
設定ファイルは`molt/config`外に置くこともできます。その際は`python molt_app.py -c path/to/molt_app.cfg`としてMoltを起動してください。詳しくは`python molt_app.py --help`を参照。

## Molt開発について
### ソースコード (必須)

- [EditorConfig](http://editorconfig.org/)
- [Flake8](http://flake8.pycqa.org/en/latest/)
- [YAPF](https://github.com/google/yapf)

### task runner

```shell
$ make help
```

### コミットメッセージ (任意)

- :new: `:new:` 新規ファイルを追加
- :art: `:art:` リファクタリング
- :construction: `:construction:` 工事中
- :memo: `:memo:` ドキュメントの記述
- :bug: `:bug:` バグの修正
- :fire: `:fure:` ファイル/ディレクトリの削除
- :white_check_mark: `:white_check_mark:` テストの追加
- :shirt: `:shirt:` Lint(Flake8)の警告を取り除いた
- :sparkles: `:sparkles:` 新機能の追加
- :tada: `:tada:` 記念すべき新機能の完成
