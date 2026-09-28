# MUUMEI 配信専用リポジトリ

正本ソースは別のPrivateリポジトリで管理します。このmainにはアプリの元コード、環境ファイル、DB定義、サーバー秘密鍵を置きません。

## 2026-09-29 / 配信ファイル準備完了

- 写真背景・黄色/白の高コントラストボタンを含む一般側の配信ファイルを `docs/` に保存済みです。
- 一般/OWNERの型検査とビルド成功。主要画面の360/390/1280px表示、リンク、画像、ボタンコントラスト、求人詳細クリック/再読込、Service Workerの適用範囲と他アプリのcache保持を含む **50項目成功**。
- 検証記録: [Actions run 36499681845](https://github.com/mumei-s/muumei-public/actions/runs/36499681845)。build成功。deployはPages未設定により停止。
- OWNERは独立パッケージとして生成しており、一般側の `docs/` にOWNERログインを公開していません。
- これは画面配信の検証です。認証済み実アカウント、LINE実送受信等の本番E2E成功ではありません。`ready=false` を維持しています。

## 公開前に必要な管理者設定

[このリポジトリのPages設定](https://github.com/mumei-s/muumei-public/settings/pages) で、**Build and deployment → Source → GitHub Actions** に設定してください。

設定後、上記実行の失敗したdeploy jobだけを再実行できます。配信artifactが期限切れの場合は、Recover and deploy MUUMEI Pages workflowを新しく実行してください。

予定URL: `https://mumei-s.github.io/muumei-public/`

Pagesの実配備と実URL確認が済むまでは、公開済み/サービス稼働済みとは扱いません。

## 正本との関係

今回の復旧は、正本とコードhashを照合済みの公開履歴から配信パッケージを生成しています。正本には最新mainを直接ビルド/検証し非公開artifactを生成する独立workflowも追加済みです。将来のソース変更を公開履歴へ手動コピーしないでください。正本から公開用ファイルだけを取り出す方針を維持します。

## 維持していること

- 既存のOWNER権限、Supabaseのデータ・RLS、LINE設定、INSIGHTは変更していません。
- 誤って配置されていた `apps/` と `scripts/` は現行mainから除去済みです。
- 過去コミットの履歴には、以前コピーしたフロントエンドの元コードが残っています。現行mainの整理は、履歴の完全消去ではありません。
