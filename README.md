# MUUMEI 配信専用リポジトリ

正本ソースは別のPrivateリポジトリで管理します。このmainにはアプリの元コード、環境ファイル、DB定義、サーバー秘密鍵を置きません。

## 2026-09-29 / 本体のGitHub Pages公開と実URL検証完了

本体の公開URL: https://mumei-s.github.io/muumei-public/

操作見本: https://mumei-s.github.io/muumei-public/demo/home/

ユーザーがPagesのSourceをGitHub Actionsへ変更した後、失敗していたdeployだけを再実行しました。

- [公開処理 run 36499681845 / attempt 2](https://github.com/mumei-s/muumei-public/actions/runs/36499681845): **success**。公開成功時刻は2026-09-29 00:05:23 UTC（09:05:23 JST）。
- [実URLのブラウザー検証 run 36501624669](https://github.com/mumei-s/muumei-public/actions/runs/36501624669): **29件成功・失敗0件**。
- 実URLのHTTP 200と配信index.htmlの完全一致を確認。SHA256: `ea4d309805867d7ccc84ea4ab5a0e47f996779bd3821212d2994122ad8b8ef73`。
- Chromiumで8画面×360/390/1280pxの24ケースを検証。写真背景、画面内画像、横はみ出し、リンクのベースパス、JS例外を確認。
- 求人詳細クリック・再読み込み、主要ボタンとフッターリンクの文字コントラスト、Service Workerの適用範囲と他キャッシュの保持も成功。
- 実URLのスクリーンショットと結果JSONをActions artifact `muumei-live-verification` に保存（14日保持）。
- 今後の公開後も独立した `Verify live MUUMEI Pages` workflowで同じ読み取り検証を実行します。アカウント作成、メッセージ送信、実データ変更はしません。

**これは一般側の公開ページ・操作見本の配信確認です。認証済み実アカウントでの運用E2E、LINE実送受信、OWNERの新しい公開先への配備が完了したという意味ではありません。ready=falseを維持しています。**

## OWNERと公開前検証

- 一般/OWNERの型検査とビルド成功。公開前の主要画面・画像・リンク・求人詳細・コントラスト・PWA範囲を含む50項目も成功済みです（上記公開処理のbuild job）。
- OWNERは独立パッケージ `muumei-owner-separate-origin-package` として生成しています。一般側の `docs/` にOWNERログインを配置していません。
- OWNERの別公開先と認証付きの実機確認は引き続き残件です。既存OWNERの公開範囲・権限を勝手に変更しません。

## 再公開について

PagesのSource設定は完了済みです。ユーザーへ同じ設定変更を再依頼しないでください。

公開後の実URL検証は `.github/workflows/verify-live-pages.yml`。配信の復旧workflowは `.github/workflows/recover-pages.yml` です。復旧workflowは保存済みrevisionを使うため、新しい正本ソースを反映する仕組みと混同しないでください。

## 正本との関係

今回の復旧は、正本とコードhashを照合済みの公開履歴から配信パッケージを生成しています。正本には最新mainを直接ビルド/検証し非公開artifactを生成する独立workflowも追加済みです。将来のソース変更を公開履歴へ手動コピーしないでください。正本から公開用ファイルだけを取り出す方針を維持します。

## 維持していること

- 既存のOWNER権限、Supabaseのデータ・RLS、LINE設定、INSIGHTは変更していません。
- 誤って配置されていた `apps/` と `scripts/` は現行mainから除去済みです。
- 過去コミットの履歴には、以前コピーしたフロントエンドの元コードが残っています。現行mainの整理は、履歴の完全消去ではありません。
