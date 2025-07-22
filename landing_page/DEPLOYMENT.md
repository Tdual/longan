# Longan LP デプロイメント手順書

## 概要
このドキュメントは、Longan のランディングページ（LP）をAWS上にデプロイし、独自ドメインで公開するための手順を記載しています。

## アーキテクチャ
- **ホスティング**: Amazon S3（静的ウェブサイトホスティング）
- **CDN**: Amazon CloudFront
- **DNS**: Amazon Route 53
- **SSL証明書**: AWS Certificate Manager (ACM)
- **ドメイン**: longan-ai.com

## 必要な前提条件
1. AWSアカウント
2. AWS CLIがインストールされ、認証情報が設定されていること
3. 以下のAWSサービスへのアクセス権限：
   - Route 53（ドメイン登録・DNS管理）
   - S3（静的ホスティング）
   - CloudFront（CDN）
   - ACM（SSL証明書）

## デプロイ手順

### 1. ドメインの取得（Route 53）
```bash
# ドメインの利用可能性を確認
aws route53domains check-domain-availability --domain-name longan-ai.com --region us-east-1

# ドメインを登録（連絡先情報が必要）
aws route53domains register-domain \
  --domain-name longan-ai.com \
  --duration-in-years 1 \
  --admin-contact [連絡先情報] \
  --registrant-contact [連絡先情報] \
  --tech-contact [連絡先情報] \
  --privacy-protect-admin-contact \
  --privacy-protect-registrant-contact \
  --privacy-protect-tech-contact \
  --auto-renew \
  --region us-east-1
```

### 2. S3バケットの作成と設定
```bash
# バケットを作成（バケット名はドメイン名と同じにする）
aws s3 mb s3://longan-ai.com --region ap-northeast-1

# 静的ウェブサイトホスティングを有効化
aws s3 website s3://longan-ai.com \
  --index-document index.html \
  --error-document error.html \
  --region ap-northeast-1

# パブリックアクセスブロックを解除
aws s3api put-public-access-block \
  --bucket longan-ai.com \
  --public-access-block-configuration "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false" \
  --region ap-northeast-1

# バケットポリシーを適用
cat > bucket-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::longan-ai.com/*"
    }
  ]
}
EOF

aws s3api put-bucket-policy \
  --bucket longan-ai.com \
  --policy file://bucket-policy.json \
  --region ap-northeast-1
```

### 3. ファイルのアップロード
```bash
# HTMLファイルをアップロード
aws s3 cp index.html s3://longan-ai.com/index.html --content-type text/html --region ap-northeast-1
aws s3 cp error.html s3://longan-ai.com/error.html --content-type text/html --region ap-northeast-1

# 画像ファイルをアップロード
aws s3 cp favicon.png s3://longan-ai.com/favicon.png --content-type image/png --region ap-northeast-1
aws s3 cp images/pdf-screen.png s3://longan-ai.com/images/pdf-screen.png --content-type image/png --region ap-northeast-1
aws s3 cp images/settings.png s3://longan-ai.com/images/settings.png --content-type image/png --region ap-northeast-1
aws s3 cp images/dialogue-edit.png s3://longan-ai.com/images/dialogue-edit.png --content-type image/png --region ap-northeast-1
```

### 4. SSL証明書の取得（ACM）
```bash
# 証明書をリクエスト（us-east-1リージョンで作成する必要がある）
aws acm request-certificate \
  --domain-name longan-ai.com \
  --subject-alternative-names www.longan-ai.com \
  --validation-method DNS \
  --region us-east-1
```

証明書のARNをメモしておく（例: arn:aws:acm:us-east-1:XXXXXXXXXXXX:certificate/XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX）

### 5. DNS検証レコードの追加
```bash
# 証明書の検証レコードを取得
aws acm describe-certificate \
  --certificate-arn [証明書のARN] \
  --region us-east-1

# Route 53に検証レコードを追加（取得した値を使用）
# ホストゾーンIDを確認
aws route53 list-hosted-zones-by-name --query "HostedZones[?Name=='longan-ai.com.']"

# 検証レコードを追加するJSONファイルを作成して適用
```

### 6. CloudFrontディストリビューションの作成
証明書の検証が完了してから実行：

```bash
# CloudFront設定ファイルを作成
cat > cloudfront-config.json << EOF
{
  "CallerReference": "longan-ai-com-$(date +%s)",
  "Comment": "Longan AI Landing Page",
  "DefaultRootObject": "index.html",
  "Origins": {
    "Quantity": 1,
    "Items": [{
      "Id": "S3-longan-ai.com",
      "DomainName": "longan-ai.com.s3-website-ap-northeast-1.amazonaws.com",
      "CustomOriginConfig": {
        "HTTPPort": 80,
        "HTTPSPort": 443,
        "OriginProtocolPolicy": "http-only"
      }
    }]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "S3-longan-ai.com",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {
      "Quantity": 2,
      "Items": ["GET", "HEAD"]
    },
    "TrustedSigners": {"Enabled": false, "Quantity": 0},
    "ForwardedValues": {
      "QueryString": false,
      "Cookies": {"Forward": "none"}
    },
    "MinTTL": 0,
    "Compress": true
  },
  "Enabled": true,
  "Aliases": {
    "Quantity": 2,
    "Items": ["longan-ai.com", "www.longan-ai.com"]
  },
  "ViewerCertificate": {
    "ACMCertificateArn": "[証明書のARN]",
    "SSLSupportMethod": "sni-only",
    "MinimumProtocolVersion": "TLSv1.2_2021"
  }
}
EOF

# ディストリビューションを作成
aws cloudfront create-distribution --distribution-config file://cloudfront-config.json
```

### 7. Route 53のDNS設定
```bash
# CloudFrontのドメイン名をメモ（例: dXXXXXXXXXXXXX.cloudfront.net）

# DNSレコードを作成
cat > route53-records.json << EOF
{
  "Changes": [
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "longan-ai.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z2FDTNDATAQYW2",
          "DNSName": "[CloudFrontのドメイン名]",
          "EvaluateTargetHealth": false
        }
      }
    },
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "www.longan-ai.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z2FDTNDATAQYW2",
          "DNSName": "[CloudFrontのドメイン名]",
          "EvaluateTargetHealth": false
        }
      }
    }
  ]
}
EOF

aws route53 change-resource-record-sets \
  --hosted-zone-id [ホストゾーンID] \
  --change-batch file://route53-records.json
```

## 更新手順

### HTMLファイルの更新
```bash
# ローカルで編集後、S3にアップロード
aws s3 cp index.html s3://longan-ai.com/index.html --content-type text/html --region ap-northeast-1

# CloudFrontのキャッシュをクリア
aws cloudfront create-invalidation \
  --distribution-id [ディストリビューションID] \
  --paths "/*"
```

### 画像の追加・更新
```bash
# 画像をアップロード
aws s3 cp [画像ファイル] s3://longan-ai.com/images/[ファイル名] --content-type image/png --region ap-northeast-1
```

## トラブルシューティング

### 403エラーが表示される場合
1. CloudFrontにカスタムドメインが設定されているか確認
2. SSL証明書が正しく設定されているか確認
3. S3バケットポリシーが正しく設定されているか確認

### 画像が表示されない場合
- HTMLファイル内の画像パスが相対パス（`/images/xxx.png`）になっているか確認
- S3の直接URLを使用していないか確認

### DNS反映待ち
- ドメイン登録：通常15分程度
- DNS変更：最大48時間（通常は数分〜数時間）
- SSL証明書検証：DNS検証レコード追加後、通常数分

## ファイル構成
```
landing_page/
├── DEPLOYMENT.md      # このファイル
├── index.html         # メインのランディングページ
├── error.html         # 404エラーページ
├── favicon.png        # ファビコン（ロゴ）
└── images/            # 画像ディレクトリ
    ├── pdf-screen.png
    ├── settings.png
    └── dialogue-edit.png
```

## 注意事項
- **リージョン**: S3はap-northeast-1、ACMはus-east-1で作成する必要がある
- **バケット名**: ドメイン名と同じにする必要がある
- **画像パス**: CloudFront経由でアクセスする場合は相対パスを使用
- **キャッシュ**: 更新後はCloudFrontのキャッシュをクリアする

## 関連リンク
- [AWS S3 静的ウェブサイトホスティング](https://docs.aws.amazon.com/ja_jp/AmazonS3/latest/userguide/WebsiteHosting.html)
- [AWS CloudFront ドキュメント](https://docs.aws.amazon.com/ja_jp/cloudfront/)
- [AWS Route 53 ドキュメント](https://docs.aws.amazon.com/ja_jp/route53/)
- [AWS Certificate Manager](https://docs.aws.amazon.com/ja_jp/acm/)