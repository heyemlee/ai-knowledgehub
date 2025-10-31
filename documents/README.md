# 文档目录

将需要导入知识库的文档放入此目录。

## 支持格式

- PDF (`.pdf`)
- Word (`.docx`, `.doc`)
- Excel (`.xlsx`, `.xls`)
- 文本 (`.txt`)

## 使用方法

1. **放入文档**：将文档文件放入此目录（可创建子目录）
2. **批量导入**：运行 `python scripts/batch_import.py`
3. **更新文档**：运行 `python scripts/update_documents.py`

## 注意事项

- 脚本会递归扫描所有子目录
- **自动去重**：如果文档已存在，会自动删除旧数据后再导入新数据（避免重复）
- **更新文档**：直接运行 `batch_import.py` 即可更新已存在的文档，或使用 `update_documents.py` 更新指定文档
- 建议文档大小不超过 50MB
