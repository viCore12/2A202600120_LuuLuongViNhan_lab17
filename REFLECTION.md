# REFLECTION — Lab 17 Multi-Memory Agent

## 1. Memory nào giúp agent nhiều nhất?

Qua 10 conversations, **profile memory** là thành phần mang giá trị nhất:
nó biến một LLM "giật mình mỗi turn" thành một trợ lý biết user là ai
ngay từ câu đầu. Ba điểm cụ thể:

- **Cost thấp** — mỗi profile fact chỉ vài token nhưng unlock được
  rất nhiều câu hỏi downstream (tên, dị ứng, sở thích, nơi ở…).
- **Hit rate cao** — hầu như mọi multi-turn conversation đều đụng tới
  ít nhất một fact đã khai báo trước.
- **Dễ debug** — JSON KV soi bằng mắt được, có history để audit.

**Semantic memory** đứng thứ 2 vì mở khóa được các câu hỏi domain
(FAQ, policy) mà profile không chứa. **Episodic** là thứ 3 vì chỉ
thật sự hữu ích khi user tham chiếu quá khứ rõ ràng. **Short-term**
là nền tảng — không có nó agent không giữ được coherence trong cùng
một phiên, nhưng một mình nó thì vô dụng với phiên sau.

## 2. Memory nào rủi ro nhất nếu retrieve sai?

**Profile memory** vừa là lợi thế lớn nhất vừa là nguồn rủi ro lớn
nhất. Lý do:

- **Chứa PII trực tiếp**: tên, địa chỉ, dị ứng (thông tin y tế), tuổi,
  công ty. Nếu log của agent bị lộ thì đây là cái đầu tiên bị khai thác.
- **Ảnh hưởng toàn bộ downstream**: một fact sai (vd. allergy bị ghi
  nhầm thành "đậu nành" khi thực ra là "sữa bò") sẽ bị LLM trích dẫn
  tự tin trong mọi response, có khả năng gây hại (gợi ý món ăn sai).
- **Conflict handling phải ưu tiên correction** — đây chính là lý do
  `ProfileMemory.set()` của lab này dùng latest-write-wins và đẩy giá
  trị cũ vào `history` thay vì append (nếu append thì LLM thấy cả hai
  giá trị và tự tiện chọn cái cũ).

Episodic memory xếp thứ 2: có thể mô tả context nhạy cảm (vd. "user
đã phàn nàn về đồng nghiệp tên X"). Semantic rủi ro thấp hơn vì là
KB do mình kiểm soát, nhưng có thể bị dính PII nếu ingest dữ liệu
chat log vào KB mà không redact.

## 3. Nếu user yêu cầu xóa memory thì xóa ở backend nào?

Chúng ta phải xóa ở **cả 4 backend** — vì một PII có thể xuất hiện
chéo nhau. Thứ tự đề xuất:

1. **Profile** — `ProfileMemory.delete(key)` (đã implement). Xóa luôn
   cả `history` để không lộ giá trị cũ.
2. **Short-term** — flush `ShortTermMemory.clear()` hoặc ít nhất loại
   các message chứa PII khỏi buffer hiện tại.
3. **Episodic** — rewrite JSONL file, loại bỏ các record có tag hoặc
   nội dung liên quan user. Tốt nhất bổ sung `user_id` vào record để
   lọc được (lab hiện tại single-user nên chưa cần).
4. **Semantic** — nếu đã ingest user text vào KB: xóa document theo
   `id` / re-embed. Với Chroma/FAISS phải rebuild index.

Ngoài ra cần: **TTL mặc định** cho episodic (vd. 90 ngày), **consent
flag** cho profile (user tick đồng ý lưu mỗi field), và **audit log
riêng** để khi deletion chạy thì có evidence đã xóa.

## 4. Điều gì sẽ làm system fail khi scale?

Bốn failure mode quan trọng:

### 4.1 Rule-based extractor bể khi input đa dạng
Hiện tại `agent/extractor.py` dùng regex tiếng Việt. Pass cho 10
scenarios trong benchmark, nhưng sẽ miss:
- Câu phức hợp ("tên mình là Linh nhưng gọi mình là Ling cũng được")
- Tiếng Anh / code-switching
- Typo, viết tắt

**Mitigation**: chuyển sang LLM-based extraction (có JSON schema +
error handling) cho production — đây chính là bonus item #3.

### 4.2 TF-IDF semantic không đủ khi KB lớn
TF-IDF scale kém về latency (O(n*|docs|) mỗi query) và không bắt được
synonym / paraphrase. "Làm sao hoàn tiền" sẽ không match "refund
policy". Với KB > vài nghìn docs bắt buộc dùng vector DB thật
(Chroma/FAISS) — bonus item #2.

### 4.3 Profile drift — không có confidence score
Agent hiện tại tin tuyệt đối vào fact extract được. Nếu user nói
sarcastically hoặc role-play, fact sai sẽ được lưu cứng. Cần:
- `confidence` score mỗi fact
- Yêu cầu user confirm với fact quan trọng (allergy, medical)
- Expiration / stale detection

### 4.4 Multi-user / cross-session isolation
Lab này dùng file `profile.json` duy nhất → không chịu được nhiều
user. Khi scale:
- Key theo `user_id` trong tất cả backend
- Đảm bảo `retrieve_memory` filter theo `user_id` — nếu không sẽ
  leak profile của user A sang response cho user B, đây là một
  trong các lỗi privacy tệ nhất có thể xảy ra.

## 5. Limitations kỹ thuật của solution hiện tại

| # | Limitation | Impact | Đề xuất |
|---|---|---|---|
| 1 | Mock LLM deterministic thay cho LLM thật | Benchmark không phản ánh chất lượng generation thực, chỉ đo "memory làm được gì" | Cắm OpenAI khi có API key (hook sẵn trong `agent/llm.py`) |
| 2 | Extractor dựa regex, tiếng Việt hardcoded | Không scale sang domain/ngôn ngữ khác | Function-calling LLM extraction |
| 3 | Semantic dùng TF-IDF, không có embedding | Không bắt synonym, khó scale | Chroma/FAISS với sentence-transformers |
| 4 | Single-user, không có auth / user_id | Không dùng được production | Thêm `user_id` làm namespace mọi backend |
| 5 | Không có TTL / deletion automation | Phụ thuộc thủ công để tuân thủ GDPR | Scheduler + consent ledger |
| 6 | Budget dùng word count, không phải token | Sai số ~20-30% tùy tokenizer | Dùng `tiktoken.encoding_for_model(...)` |
| 7 | Không có rate limit / guardrail cho writes | Adversarial user có thể spam fake facts vào profile | Giới hạn writes/phút, require confirmation cho field nhạy cảm |

## 6. Privacy-by-design — các điều đã có và nên thêm

**Đã có trong lab:**
- `ProfileMemory.delete()` xóa cả history → GDPR-style right-to-erasure.
- `source` field (`user_stated` / `user_correction`) ghi nguồn gốc fact.
- Profile history giữ giá trị cũ có timestamp → audit.
- Benchmark tách no-memory/with-memory để quantify risk surface.

**Nên thêm:**
- Consent prompt trước khi lưu field nhạy cảm (allergy, age, địa chỉ).
- TTL: episodic 90 ngày, semantic ingest 1 năm, profile không TTL
  nhưng có "last-confirmed" timestamp và prompt user xác nhận lại
  sau 6 tháng.
- PII redaction khi log prompt ra stdout / monitoring.
- Separate encryption-at-rest cho file `profile.json` (hiện tại
  plaintext — đủ cho lab, không đủ cho production).
