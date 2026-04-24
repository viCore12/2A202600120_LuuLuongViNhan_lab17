# BENCHMARK — Lab 17 Multi-Memory Agent

**LLM:** OpenAI `gpt-4o-mini`  
**Graph:** LangGraph thật (`StateGraph`)  
**Token counter:** tiktoken (`cl100k_base`)  

So sánh **no-memory baseline** vs **with-memory agent** trên 10 multi-turn conversations.

## Summary

- Pass @ no-memory: **0/10**
- Pass @ with-memory: **10/10**
- Avg prompt tokens (final turn) — no-memory: 49 | with-memory: 167

### Coverage các nhóm test

| Nhóm test | # conversations | Pass (with-memory) |
|---|---:|---:|
| budget_trim | 1 | 1/1 |
| conflict_update | 2 | 2/2 |
| episodic_recall | 2 | 2/2 |
| profile_recall | 2 | 2/2 |
| semantic_retrieval | 3 | 3/3 |

## Kết quả tổng hợp

| # | Category | Scenario | No-memory result | With-memory result | Pass? |
|---|---|---|---|---|:-:|
| 1 | profile_recall | Recall user name after 6 turns | Xin lỗi, tôi chưa biết tên của bạn. | Tên bạn là Linh. | ✅ |
| 2 | conflict_update | Allergy conflict — sữa bò → đậu nành | Xin lỗi, nhưng tôi không có thông tin về tình trạng dị ứng … | Bạn bị dị ứng đậu nành. Nếu bạn cần thêm thông tin hoặc lời… | ✅ |
| 3 | episodic_recall | Recall previous debug lesson về docker | Xin lỗi, mình chưa biết thông tin về lỗi container không kế… | Lần trước, bạn đã fix bug docker networking bằng cách sử dụ… | ✅ |
| 4 | semantic_retrieval | Retrieve FAQ: chính sách hoàn tiền | Xin lỗi, mình chưa biết thông tin về chính sách hoàn tiền c… | Chính sách hoàn tiền của công ty quy định rằng khách hàng đ… | ✅ |
| 5 | budget_trim | Long conversation but still recall name | Xin lỗi, nhưng tôi chưa biết tên của bạn. | Tên bạn là Minh. | ✅ |
| 6 | profile_recall | Recall favorite food và city cùng lúc | Chưa biết món ăn bạn thích là gì. Bạn có thể cho tôi biết t… | Bạn thích ăn mì Quảng! Đây là một món ăn rất đặc trưng và n… | ✅ |
| 7 | conflict_update | Location correction — Hà Nội → Sài Gòn | Xin lỗi, tôi chưa biết bạn sống ở đâu. | Bạn sống ở Sài Gòn. Nếu bạn cần thông tin gì về Sài Gòn, hã… | ✅ |
| 8 | semantic_retrieval | Retrieve FAQ: reset mật khẩu | Chưa biết. | Link reset mật khẩu có hiệu lực trong 30 phút. | ✅ |
| 9 | semantic_retrieval | Retrieve FAQ: chính sách PII bảo mật | Xin lỗi, nhưng tôi chưa biết thông tin về chính sách bảo mậ… | Chính sách bảo mật PII của công ty quy định rằng dữ liệu cá… | ✅ |
| 10 | episodic_recall | Episodic + budget: recall sau 5 turn xen kẽ | Xin lỗi, mình chưa biết bạn đã làm gì để xử lý bug auth lần… | Lần trước, bạn đã sửa bug auth bằng cách đổi JWT secret. Nế… | ✅ |

## Transcripts chi tiết

### Conversation #1 — Recall user name after 6 turns

**Category:** `profile_recall` — **Expected substring:** `Linh`

**Turns (with-memory mode):**

- user: Chào bạn, tên tôi là Linh.
  - assistant: Chào Linh! Rất vui được gặp bạn. Bạn cần giúp gì hôm nay?
  - prompt_tokens: 129, writes: 1
- user: Tôi sống ở Hà Nội.
  - assistant: Rất tốt, Linh! Hà Nội là một thành phố đẹp và có nhiều điều thú vị. Bạn có muốn chia sẻ thêm về sở thích hoặc những điều bạn thích làm ở Hà Nội không?
  - prompt_tokens: 150, writes: 1
- user: Tôi làm việc tại công ty BlueBolt.
  - assistant: Rất tốt, Linh! Bạn làm việc tại công ty BlueBolt. Bạn có cần thông tin gì liên quan đến công việc hoặc công ty không?
  - prompt_tokens: 192, writes: 1
- user: Tôi thích lập trình bằng Python.
  - assistant: Thật tuyệt vời! Python là một ngôn ngữ lập trình rất mạnh mẽ và linh hoạt. Bạn thường làm việc với những dự án nào bằng Python?
  - prompt_tokens: 185, writes: 1
- user: Hôm nay trời đẹp nhỉ.
  - assistant: Đúng vậy, Hà Nội thường có những ngày trời đẹp. Bạn có kế hoạch gì cho ngày hôm nay không?
  - prompt_tokens: 108, writes: 0
- user: Cảm ơn vì đã trò chuyện.
  - assistant: Không có gì đâu, Linh! Nếu bạn cần bất kỳ thông tin hay hỗ trợ nào khác, hãy cho tôi biết nhé!
  - prompt_tokens: 172, writes: 0
- user: Tên tôi là gì?
  - assistant: Tên bạn là Linh.
  - prompt_tokens: 179, writes: 0

**Assertion turn — no-memory answer:** `Xin lỗi, tôi chưa biết tên của bạn.`
**Assertion turn — with-memory answer:** `Tên bạn là Linh.`
**Result:** Pass ✅

---

### Conversation #2 — Allergy conflict — sữa bò → đậu nành

**Category:** `conflict_update` — **Expected substring:** `đậu nành`

**Turns (with-memory mode):**

- user: Tôi dị ứng sữa bò.
  - assistant: Cảm ơn bạn đã chia sẻ! Nếu bạn cần thông tin hoặc lời khuyên về chế độ ăn uống hoặc cách xử lý dị ứng sữa bò, hãy cho tôi biết nhé!
  - prompt_tokens: 110, writes: 1
- user: À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò.
  - assistant: Cảm ơn bạn đã cập nhật thông tin! Nếu bạn cần hỗ trợ hoặc thông tin gì liên quan đến dị ứng đậu nành, hãy cho tôi biết nhé!
  - prompt_tokens: 197, writes: 1
- user: Tôi bị dị ứng gì?
  - assistant: Bạn bị dị ứng đậu nành. Nếu bạn cần thêm thông tin hoặc lời khuyên về cách xử lý dị ứng này, hãy cho tôi biết nhé!
  - prompt_tokens: 164, writes: 0

**Assertion turn — no-memory answer:** `Xin lỗi, nhưng tôi không có thông tin về tình trạng dị ứng của bạn. Bạn nên tham khảo ý kiến bác sĩ…`
**Assertion turn — with-memory answer:** `Bạn bị dị ứng đậu nành. Nếu bạn cần thêm thông tin hoặc lời khuyên về cách xử lý dị ứng này, hãy ch…`
**Result:** Pass ✅

---

### Conversation #3 — Recall previous debug lesson về docker

**Category:** `episodic_recall` — **Expected substring:** `service`

**Turns (with-memory mode):**

- user: Mình đã fix bug docker networking bằng cách dùng service name thay vì localhost.
  - assistant: Tuyệt vời! Việc sử dụng service name thay vì localhost trong Docker networking là một cách giải quyết phổ biến cho vấn đề kết nối giữa các service. Nếu bạn cần thêm thông tin hay hỗ trợ gì khác, hãy cho mình biết nhé!
  - prompt_tokens: 117, writes: 1
- user: Sau đó deploy production thì ổn.
  - assistant: Rất tốt! Khi bạn đã deploy ứng dụng lên production và mọi thứ hoạt động ổn, hãy nhớ tắt debug mode và sử dụng gunicorn hoặc uvicorn để đảm bảo hiệu suất và bảo mật cho ứng dụng của bạn. Nếu bạn cần thêm thông tin hay có câu hỏi nào khác, hãy cho mình biết nhé!
  - prompt_tokens: 170, writes: 0
- user: Hôm nay lại gặp lỗi container không kết nối, lần trước bug docker mình làm gì?
  - assistant: Lần trước, bạn đã fix bug docker networking bằng cách sử dụng service name thay vì localhost. Nguyên nhân phổ biến khi container Docker không kết nối được tới service khác là do dùng sai hostname. Bạn có thể kiểm tra lại xem mình đã sử dụng đúng service name trong docker-compose chưa nhé!
  - prompt_tokens: 252, writes: 0

**Assertion turn — no-memory answer:** `Xin lỗi, mình chưa biết thông tin về lỗi container không kết nối hoặc bug docker mà bạn đã gặp trướ…`
**Assertion turn — with-memory answer:** `Lần trước, bạn đã fix bug docker networking bằng cách sử dụng service name thay vì localhost. Nguyê…`
**Result:** Pass ✅

---

### Conversation #4 — Retrieve FAQ: chính sách hoàn tiền

**Category:** `semantic_retrieval` — **Expected substring:** `14 ngày`

**Turns (with-memory mode):**

- user: Cho mình hỏi tí về chính sách.
  - assistant: Bạn có thể cho mình biết bạn muốn hỏi về chính sách nào không? Mình sẽ cố gắng giúp bạn!
  - prompt_tokens: 130, writes: 0
- user: Chính sách hoàn tiền của công ty thế nào?
  - assistant: Chính sách hoàn tiền của công ty quy định rằng khách hàng được hoàn tiền 100% trong vòng 14 ngày kể từ ngày mua nếu sản phẩm còn nguyên seal. Sau 14 ngày, công ty chỉ hỗ trợ đổi sản phẩm tương đương, không hoàn tiền mặt. Nếu bạn cần thêm thông tin, hãy cho mình biết nhé!
  - prompt_tokens: 144, writes: 0

**Assertion turn — no-memory answer:** `Xin lỗi, mình chưa biết thông tin về chính sách hoàn tiền của công ty. Bạn có thể cung cấp thêm chi…`
**Assertion turn — with-memory answer:** `Chính sách hoàn tiền của công ty quy định rằng khách hàng được hoàn tiền 100% trong vòng 14 ngày kể…`
**Result:** Pass ✅

---

### Conversation #5 — Long conversation but still recall name

**Category:** `budget_trim` — **Expected substring:** `Minh`

**Turns (with-memory mode):**

- user: Tên tôi là Minh.
  - assistant: Chào Minh! Rất vui được gặp bạn. Bạn cần giúp gì hôm nay?
  - prompt_tokens: 127, writes: 1
- user: Tôi đang học về LangGraph.
  - assistant: LangGraph nghe có vẻ thú vị! Bạn đang học về khía cạnh nào của LangGraph?
  - prompt_tokens: 90, writes: 0
- user: Hôm qua tôi đọc về memory stack.
  - assistant: Memory stack là một khái niệm quan trọng trong lập trình và quản lý bộ nhớ. Bạn đã tìm hiểu được những gì về memory stack?
  - prompt_tokens: 154, writes: 0
- user: Hôm nay tôi code lab 17.
  - assistant: Tuyệt vời! Bạn đang làm gì trong lab 17? Có điều gì bạn cần hỗ trợ không?
  - prompt_tokens: 121, writes: 0
- user: Tôi dự định dùng Chroma cho semantic.
  - assistant: Chroma là một lựa chọn tốt cho việc xử lý semantic. Bạn đã có kế hoạch cụ thể nào cho việc sử dụng Chroma trong dự án của mình chưa?
  - prompt_tokens: 180, writes: 0
- user: Mình thấy TF-IDF cũng đủ cho lab.
  - assistant: TF-IDF là một phương pháp phổ biến trong việc xử lý văn bản và tìm kiếm thông tin. Nó giúp xác định tầm quan trọng của từ trong tài liệu so với toàn bộ tập hợp tài liệu. Nếu bạn thấy nó đủ cho lab, có thể bạn đã nắm vững cách áp dụng nó. Bạn có cần thêm thông tin hay hỗ trợ gì không?
  - prompt_tokens: 130, writes: 0
- user: Đang nghĩ về prompt injection pattern.
  - assistant: Prompt injection pattern là một khái niệm thú vị trong lĩnh vực trí tuệ nhân tạo và xử lý ngôn ngữ tự nhiên. Bạn đã tìm hiểu được những gì về nó? Có điều gì cụ thể bạn muốn thảo luận không?
  - prompt_tokens: 132, writes: 0
- user: Buffer ngắn để tiết kiệm token.
  - assistant: Chưa biết thông tin cụ thể về buffer ngắn để tiết kiệm token. Bạn có thể giải thích thêm về điều này không?
  - prompt_tokens: 155, writes: 0
- user: Ủa mà tên tôi là gì nhỉ?
  - assistant: Tên bạn là Minh.
  - prompt_tokens: 178, writes: 0

**Assertion turn — no-memory answer:** `Xin lỗi, nhưng tôi chưa biết tên của bạn.`
**Assertion turn — with-memory answer:** `Tên bạn là Minh.`
**Result:** Pass ✅

---

### Conversation #6 — Recall favorite food và city cùng lúc

**Category:** `profile_recall` — **Expected substring:** `mì Quảng`

**Turns (with-memory mode):**

- user: Tôi sống ở Đà Nẵng.
  - assistant: Chào bạn! Rất vui được biết bạn sống ở Đà Nẵng. Nếu bạn cần thông tin gì hoặc có câu hỏi nào, hãy cho tôi biết nhé!
  - prompt_tokens: 128, writes: 1
- user: Tôi thích ăn mì Quảng.
  - assistant: Mì Quảng là một món ăn đặc sản rất nổi tiếng ở Đà Nẵng! Nó có hương vị thơm ngon và thường được chế biến với nhiều loại nguyên liệu khác nhau như tôm, thịt gà, hoặc thịt heo. Bạn có món mì Quảng nào yêu thích không?
  - prompt_tokens: 106, writes: 1
- user: Món ăn tôi thích ăn gì?
  - assistant: Bạn thích ăn mì Quảng! Đây là một món ăn rất đặc trưng và ngon miệng. Nếu bạn cần gợi ý về nơi ăn mì Quảng ở Đà Nẵng, hãy cho tôi biết nhé!
  - prompt_tokens: 117, writes: 0

**Assertion turn — no-memory answer:** `Chưa biết món ăn bạn thích là gì. Bạn có thể cho tôi biết thêm thông tin không?`
**Assertion turn — with-memory answer:** `Bạn thích ăn mì Quảng! Đây là một món ăn rất đặc trưng và ngon miệng. Nếu bạn cần gợi ý về nơi ăn m…`
**Result:** Pass ✅

---

### Conversation #7 — Location correction — Hà Nội → Sài Gòn

**Category:** `conflict_update` — **Expected substring:** `Sài Gòn`

**Turns (with-memory mode):**

- user: Tôi sống ở Hà Nội.
  - assistant: Chào bạn! Rất vui được biết bạn sống ở Hà Nội. Nếu bạn có câu hỏi hay cần thông tin gì, hãy cho tôi biết nhé!
  - prompt_tokens: 128, writes: 1
- user: À thực ra mình mới chuyển vào Sài Gòn rồi.
  - assistant: Chào bạn! Vậy là bạn đã chuyển vào Sài Gòn. Hy vọng bạn sẽ có những trải nghiệm thú vị ở đó! Nếu bạn cần thông tin gì về Sài Gòn, hãy cho tôi biết nhé!
  - prompt_tokens: 110, writes: 1
- user: Tôi sống ở đâu?
  - assistant: Bạn sống ở Sài Gòn. Nếu bạn cần thông tin gì về Sài Gòn, hãy cho tôi biết nhé!
  - prompt_tokens: 173, writes: 0

**Assertion turn — no-memory answer:** `Xin lỗi, tôi chưa biết bạn sống ở đâu.`
**Assertion turn — with-memory answer:** `Bạn sống ở Sài Gòn. Nếu bạn cần thông tin gì về Sài Gòn, hãy cho tôi biết nhé!`
**Result:** Pass ✅

---

### Conversation #8 — Retrieve FAQ: reset mật khẩu

**Category:** `semantic_retrieval` — **Expected substring:** `30 phút`

**Turns (with-memory mode):**

- user: Tôi quên mật khẩu thì sao?
  - assistant: Nếu bạn quên mật khẩu, bạn có thể truy cập trang đăng nhập, bấm vào "Quên mật khẩu", sau đó nhập email đã đăng ký. Hệ thống sẽ gửi cho bạn một link để reset mật khẩu, link này có hiệu lực trong 30 phút. Nếu bạn không nhận được email, hãy kiểm tra thư mục Spam trước khi liên hệ với bộ phận hỗ trợ.
  - prompt_tokens: 121, writes: 0
- user: Link reset mật khẩu có thời hạn bao lâu?
  - assistant: Link reset mật khẩu có hiệu lực trong 30 phút.
  - prompt_tokens: 130, writes: 0

**Assertion turn — no-memory answer:** `Chưa biết.`
**Assertion turn — with-memory answer:** `Link reset mật khẩu có hiệu lực trong 30 phút.`
**Result:** Pass ✅

---

### Conversation #9 — Retrieve FAQ: chính sách PII bảo mật

**Category:** `semantic_retrieval` — **Expected substring:** `AES-256`

**Turns (with-memory mode):**

- user: Chính sách bảo mật PII của công ty thế nào?
  - assistant: Chính sách bảo mật PII của công ty quy định rằng dữ liệu cá nhân của người dùng (bao gồm tên, email, số điện thoại, địa chỉ) được lưu mã hóa bằng AES-256 trong cơ sở dữ liệu. Thời gian lưu trữ mặc định là 2 năm kể từ lần đăng nhập cuối cùng; sau đó, dữ liệu sẽ được tự động ẩn danh. Người dùng cũng có thể yêu cầu xóa dữ liệu ngay lập tức bằng cách gửi yêu cầu tới địa chỉ email privacy@example.com.
  - prompt_tokens: 133, writes: 0

**Assertion turn — no-memory answer:** `Xin lỗi, nhưng tôi chưa biết thông tin về chính sách bảo mật PII của công ty.`
**Assertion turn — with-memory answer:** `Chính sách bảo mật PII của công ty quy định rằng dữ liệu cá nhân của người dùng (bao gồm tên, email…`
**Result:** Pass ✅

---

### Conversation #10 — Episodic + budget: recall sau 5 turn xen kẽ

**Category:** `episodic_recall` — **Expected substring:** `JWT`

**Turns (with-memory mode):**

- user: Mình đã sửa bug auth bằng cách đổi JWT secret.
  - assistant: Chúc mừng bạn đã sửa được bug auth! Việc đổi JWT secret là một bước quan trọng để bảo mật hệ thống. Nếu bạn cần thêm thông tin hay hỗ trợ gì khác, hãy cho mình biết nhé!
  - prompt_tokens: 133, writes: 1
- user: Tên tôi là Nam.
  - assistant: Chào Nam! Rất vui được gặp bạn. Nếu bạn có câu hỏi hay cần hỗ trợ gì, hãy cho mình biết nhé!
  - prompt_tokens: 176, writes: 1
- user: Tôi thích ăn phở.
  - assistant: Phở là một món ăn rất ngon và nổi tiếng của Việt Nam! Bạn thích phở bò hay phở gà hơn?
  - prompt_tokens: 125, writes: 1
- user: Hôm nay mệt quá.
  - assistant: Mình rất tiếc khi nghe bạn cảm thấy mệt. Có thể bạn đã có một ngày dài hoặc có nhiều việc phải làm. Nếu bạn muốn chia sẻ thêm về lý do bạn mệt, mình sẵn sàng lắng nghe! Hoặc nếu bạn cần một món ăn ngon để thư giãn, phở có thể là một lựa chọn tuyệt vời đấy!
  - prompt_tokens: 128, writes: 0
- user: Lần trước bug auth mình làm gì nhỉ?
  - assistant: Lần trước, bạn đã sửa bug auth bằng cách đổi JWT secret. Nếu bạn cần thêm thông tin hay hỗ trợ gì khác, hãy cho mình biết nhé!
  - prompt_tokens: 197, writes: 0

**Assertion turn — no-memory answer:** `Xin lỗi, mình chưa biết bạn đã làm gì để xử lý bug auth lần trước. Bạn có thể cung cấp thêm thông t…`
**Assertion turn — with-memory answer:** `Lần trước, bạn đã sửa bug auth bằng cách đổi JWT secret. Nếu bạn cần thêm thông tin hay hỗ trợ gì k…`
**Result:** Pass ✅

---
