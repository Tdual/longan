# Gen Movie API

PDFから動画を生成するREST APIです。

## エンドポイント

### 1. PDFアップロード
```
POST /api/jobs/upload
Content-Type: multipart/form-data

file: PDFファイル
```

**レスポンス:**
```json
{
  "job_id": "uuid",
  "message": "ジョブを作成しました"
}
```

### 2. ジョブステータス確認
```
GET /api/jobs/{job_id}/status
```

**レスポンス:**
```json
{
  "job_id": "uuid",
  "status": "pending|processing|completed|failed",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00",
  "progress": 50,
  "message": "処理中です",
  "result_url": "/api/jobs/{job_id}/download",
  "error": null
}
```

### 3. 音声生成開始
```
POST /api/jobs/{job_id}/generate-audio
Content-Type: application/json

{
  "job_id": "uuid",
  "speed_scale": 1.0,
  "pitch_scale": 0.0,
  "intonation_scale": 1.2,
  "volume_scale": 1.0
}
```

### 4. 動画作成開始
```
POST /api/jobs/{job_id}/create-video
Content-Type: application/json

{
  "job_id": "uuid",
  "slide_numbers": [1, 2, 3]  // オプション
}
```

### 5. 動画ダウンロード
```
GET /api/jobs/{job_id}/download
```

### 6. ジョブ一覧
```
GET /api/jobs
```

### 7. ジョブ削除
```
DELETE /api/jobs/{job_id}
```

## ステータスフロー

1. `pending` - ジョブ作成直後
2. `slides_ready` - PDF→スライド変換完了
3. `generating_audio` - 音声生成中
4. `audio_ready` - 音声生成完了
5. `creating_video` - 動画作成中
6. `completed` - 完了
7. `failed` - エラー

## 起動方法

```bash
cd api
pip install -r requirements.txt
python main.py
```

または

```bash
uvicorn api.main:app --reload
```

## Swagger UI

http://localhost:8000/docs でAPIドキュメントを確認できます。