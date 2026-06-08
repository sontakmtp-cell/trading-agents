# Design System: TradingAgents Research Desk

Tài liệu này là nguồn thiết kế duy nhất để Google Stitch tạo giao diện web cho
TradingAgents. Ứng dụng biến quy trình nhiều AI agent hiện chạy trong terminal
thành một bàn phân tích tài chính dễ hiểu, minh bạch và có thể theo dõi theo thời
gian thực.

> TradingAgents phục vụ nghiên cứu. Mọi màn hình có quyết định giao dịch phải
> hiển thị rõ: "Không phải lời khuyên đầu tư."

## 1. Mục tiêu sản phẩm

### Người dùng chính

- Nhà đầu tư cá nhân muốn nhận một bản phân tích nhiều chiều nhưng không cần hiểu
  cách hệ thống AI vận hành.
- Người nghiên cứu muốn xem từng nguồn lập luận, tiến trình agent và báo cáo đầy
  đủ.
- Người vận hành cần chọn model, nguồn dữ liệu, độ sâu nghiên cứu và tiếp tục một
  phiên phân tích bị gián đoạn.

### Công việc quan trọng nhất

1. Bắt đầu một phân tích mới cho cổ phiếu hoặc crypto.
2. Biết hệ thống đang làm đến đâu và agent nào đang làm việc.
3. Hiểu quyết định cuối cùng trước khi đọc báo cáo dài.
4. So sánh lập luận tăng giá, giảm giá và các góc nhìn rủi ro.
5. Mở, tải xuống hoặc xem lại báo cáo cũ.

### Nguyên tắc trải nghiệm

- **Kết luận trước, bằng chứng sau:** BUY, HOLD hoặc SELL phải được nhìn thấy
  ngay; lý do, mức giá và rủi ro nằm ngay bên dưới.
- **Ngôn ngữ dành cho con người:** ưu tiên "Đang đọc tin tức" thay vì tên tool
  hoặc thuật ngữ nội bộ. Chi tiết kỹ thuật nằm trong khu vực có thể mở rộng.
- **Minh bạch, không phô diễn:** cho thấy các agent đang làm gì nhưng không biến
  giao diện thành terminal giả.
- **Không tô màu cảm xúc:** BUY, HOLD và SELL không dùng ba màu xanh, vàng, đỏ.
  Chúng dùng cùng một màu nhấn; khác biệt được thể hiện bằng chữ, biểu tượng và
  cấu trúc.

## 2. Visual Theme & Atmosphere

Một giao diện dark-mode điềm tĩnh, chính xác và có chiều sâu, giống bàn làm việc
của nhóm nghiên cứu thị trường vào buổi tối. Không khí chuyên nghiệp nhưng không
lạnh lẽo; dữ liệu dày nhưng luôn có thứ tự đọc rõ ràng.

- **Density:** 8/10: Cockpit Dense. Nhiều thông tin trên desktop, nhưng mỗi khu
  vực chỉ phục vụ một câu hỏi.
- **Variance:** 6/10: Offset Asymmetric. Bố cục bất đối xứng có kiểm soát; quyết
  định và nội dung chính rộng hơn phần trạng thái.
- **Motion:** 5/10: Fluid CSS. Chuyển động nhỏ, có mục đích, không gây xao nhãng
  khi đọc số liệu.
- **Visual signature:** các đường mảnh biểu diễn dòng nghiên cứu đi từ Analyst →
  Research → Trader → Risk → Portfolio; không dùng sơ đồ rối hoặc đường phát
  sáng neon.
- **Texture:** phủ một lớp grain cực nhẹ, opacity 1.5-2%, cố định trên nền để giảm
  cảm giác phẳng.

## 3. Color Palette & Roles

Chỉ dùng một màu nhấn. Mọi màu trạng thái phụ phải là biến thể sáng/tối hoặc
opacity của bảng màu trung tính và màu nhấn này.

- **Night Ledger** (`#0C0F0E`): nền ứng dụng chính; không dùng pure black.
- **Raised Slate** (`#141917`): khu vực nổi, thanh điều hướng, bảng điều khiển.
- **Active Surface** (`#1B211F`): trạng thái hover, hàng được chọn, skeleton.
- **Ledger Line** (`#2A332F`): đường phân cách và viền cấu trúc 1px.
- **Paper Ink** (`#F2F5F3`): chữ chính và số liệu quan trọng.
- **Quiet Alloy** (`#9AA59F`): mô tả, nhãn phụ và metadata.
- **Faint Alloy** (`#66716B`): trạng thái chưa chạy, placeholder, chữ bị vô hiệu.
- **Verdigris Signal** (`#42B883`): màu nhấn duy nhất cho CTA, focus ring, agent
  đang chạy, dữ liệu được chọn và đường tiến trình.
- **Signal Wash** (`rgba(66, 184, 131, 0.12)`): nền chọn nhẹ.
- **Signal Border** (`rgba(66, 184, 131, 0.42)`): viền focus và trạng thái active.
- **Tinted Shadow** (`rgba(3, 12, 8, 0.42)`): shadow nhẹ cùng sắc với nền.

### Quy tắc màu cho quyết định và cảnh báo

- BUY, HOLD và SELL đều dùng **Paper Ink** cho chữ và **Verdigris Signal** cho
  dấu chỉ thị. Không dùng màu xanh/đỏ để ngầm khuyến khích hành động.
- Cảnh báo rủi ro dùng viền nét đứt **Quiet Alloy**, biểu tượng rõ ràng và ngôn
  ngữ trực tiếp. Không thêm màu nhấn thứ hai.
- Biểu đồ giá dùng **Paper Ink** cho đường giá, **Verdigris Signal** cho điểm đang
  được chọn, và các sắc độ **Quiet Alloy** cho dữ liệu so sánh.

## 4. Typography Rules

- **Display và UI:** `Satoshi Variable`, fallback `Arial, sans-serif`. Tiêu đề
  track-tight, không dùng chữ quá lớn trong dashboard.
- **Số liệu và metadata:** `JetBrains Mono`, fallback `Consolas, monospace`. Mọi
  giá, phần trăm, ngày, thời gian, token và mã ticker đều dùng tabular figures.
- **Cỡ chữ cơ sở:** 16px desktop, tối thiểu 14px cho metadata; body line-height
  1.6.
- **Tiêu đề trang:** `clamp(2rem, 4vw, 4.5rem)`, weight 600, line-height 0.98.
- **Tiêu đề khu vực:** 20-24px, weight 600.
- **Nhãn nhỏ:** 11-12px, letter-spacing 0.08em, dùng sentence case; hạn chế
  all-caps.
- **Đoạn giải thích:** tối đa 65 ký tự mỗi dòng.
- **Không dùng serif** trong bất kỳ màn hình nào.
- **Banned:** Inter, Times New Roman, Georgia, Garamond, Palatino và chữ gradient.

## 5. Information Architecture

### Điều hướng toàn cục

Desktop dùng top navigation mảnh, không dùng sidebar cố định:

- Logo chữ **TradingAgents**
- `Overview`
- `New analysis`
- `Reports`
- `Settings`
- Bên phải: command button tìm ticker hoặc báo cáo bằng `Ctrl/Cmd + K`

Mobile dùng thanh trên cùng có logo, tên trang và nút menu. Menu mở thành sheet
toàn chiều rộng, không che mất ngữ cảnh hiện tại.

### Sáu màn hình cốt lõi

#### A. Overview: bàn làm việc

Mục đích: cho người dùng biết việc gì cần chú ý ngay hôm nay.

- Header lệch trái: lời chào ngắn, ngày hiện tại và CTA duy nhất `New analysis`.
- Dải **Recent decisions** rộng, hiển thị các phiên gần đây theo danh sách:
  ticker, loại tài sản, ngày phân tích, BUY/HOLD/SELL, mục tiêu giá, thời hạn và
  thời điểm hoàn tất.
- Khu **Active runs** chỉ xuất hiện khi có phiên đang chạy hoặc có thể tiếp tục.
- Khu **Research memory** tóm tắt các bài học từ quyết định cũ; là nội dung phụ,
  không giả vờ là hiệu suất đầu tư khi chưa có dữ liệu thật.
- Empty state: giải thích ngắn quy trình năm bước và CTA `Start first analysis`.

#### B. New analysis: thiết lập phiên

Mục đích: thay thế tám bước hỏi trong CLI bằng một form rõ ràng.

Bố cục desktop chia 7/5:

- Cột chính chứa bốn nhóm theo thứ tự:
  1. **Asset:** ticker, loại tài sản tự nhận diện, ngày phân tích.
  2. **Research team:** chọn Market, Sentiment, News, Fundamentals.
  3. **Research depth:** Quick, Standard, Deep; mô tả thời gian và chi phí tương
     đối, không dùng con số giả.
  4. **Output:** ngôn ngữ báo cáo và bật/tắt checkpoint.
- Cột phụ là **Run summary** cố định trong vùng nhìn: những gì sẽ chạy, model đang
  dùng và cảnh báo API key nếu thiếu.
- Provider, shallow model, deep model và reasoning effort nằm trong phần
  `Advanced model settings` có thể mở rộng. Người mới không phải đối diện chúng
  ngay.
- CTA duy nhất: `Start analysis`.
- Khi ticker hợp lệ, hiển thị tên tài sản và sàn giao dịch để người dùng xác nhận
  họ đang phân tích đúng mã.

#### C. Live analysis: phòng nghiên cứu đang chạy

Mục đích: theo dõi tiến trình mà không cần đọc log kỹ thuật.

Bố cục desktop bất đối xứng 4/8:

- Cột trái: **Research pipeline** dạng danh sách dọc gồm năm chặng Analyst,
  Research, Trader, Risk, Portfolio. Mỗi chặng mở ra danh sách agent.
- Trạng thái agent gồm `Waiting`, `Working`, `Complete`, `Needs attention`.
  Agent đang chạy có một chấm Verdigris pulse chậm; agent hoàn tất đứng yên.
- Cột phải: **Current finding** hiển thị nội dung mới nhất từ agent, ưu tiên tiêu
  đề, luận điểm và dữ liệu nguồn. Không tự cuộn khi người dùng đang đọc.
- Phía dưới current finding: **Activity details** thu gọn, chứa tool calls, model,
  token và timestamp cho người dùng chuyên sâu.
- Thanh sticky phía dưới desktop hiển thị tiến trình, thời gian đã chạy, số agent,
  số báo cáo và hành động `Stop after current step`.
- Khi checkpoint tồn tại, hiển thị banner nhỏ `Resume available` cùng hành động
  rõ ràng; không dùng modal.

#### D. Decision: kết luận danh mục

Mục đích: trả lời "nên làm gì và tại sao?" trong vòng vài giây.

- Khối đầu trang không căn giữa. Bên trái là ticker, tên tài sản, ngày phân tích;
  bên phải là metadata phiên.
- **Decision statement** chiếm nhiều không gian nhất: BUY/HOLD/SELL bằng chữ lớn,
  bên dưới là một câu tóm tắt quyết định bằng ngôn ngữ đời thường.
- Dải số liệu ngay dưới: price target, stop loss, time horizon và mức giá tham
  chiếu nếu dữ liệu thật có sẵn. Không hiển thị trường không có dữ liệu.
- Khu **Why this decision** là danh sách 3-5 luận điểm ngắn có liên kết tới bằng
  chứng trong báo cáo.
- Khu **Conditions that would change the decision** nêu rõ tín hiệu cần theo dõi.
- Disclaimer "Không phải lời khuyên đầu tư" luôn thấy mà không cần cuộn.
- CTA chính: `Open full report`. Hành động phụ là text link `Download report`.

#### E. Full report: báo cáo phân tích

Mục đích: đọc báo cáo dài, so sánh quan điểm và truy nguồn kết luận.

- Desktop chia 3/9. Mục lục bên trái sticky, nội dung báo cáo bên phải.
- Mục lục theo đúng quy trình:
  `Analyst team → Research debate → Trader plan → Risk debate → Portfolio decision`.
- Bốn báo cáo analyst dùng các section nối tiếp bằng divider, không dùng bốn card
  ngang bằng nhau.
- **Bull vs Bear** dùng bố cục hai cột đối chiếu trên desktop; hai cột có nhãn rõ
  và cùng chiều rộng. Trên mobile xếp Bull trước, Bear sau.
- **Risk debate** dùng ba tab Aggressive, Neutral, Conservative; mặc định mở
  Neutral. Tab chỉ đổi nội dung, không mở modal.
- Những con số và câu trực tiếp dẫn đến quyết định có marker Verdigris nhỏ và
  anchor link.
- Sticky mini-summary ở cuối viewport: quyết định, target, stop loss và liên kết
  quay về đầu trang.

#### F. Reports: lịch sử nghiên cứu

Mục đích: tìm và mở lại phiên phân tích đã lưu.

- Bảng là cấu trúc chính, không dùng lưới card.
- Cột: ticker, asset, analysis date, decision, price target, horizon, completed,
  report status.
- Có tìm kiếm ticker, bộ lọc loại tài sản, quyết định và khoảng ngày.
- Một hàng mở rộng inline để xem executive summary; không dùng modal.
- Mobile chuyển mỗi hàng thành khối nội dung dọc, giữ đúng thứ tự ưu tiên.

## 6. Core Components

### Buttons

- Primary button dùng nền Verdigris Signal, chữ Night Ledger, góc 10px, chiều cao
  tối thiểu 44px.
- Hover tăng nhẹ độ sáng nền; active dịch xuống 1px và scale 0.985.
- Secondary dùng nền trong suốt và border Ledger Line. Tertiary là text link.
- Không có outer glow, gradient, icon thừa hoặc nhiều hơn một primary CTA trong
  cùng một khu vực.

### Inputs and selection controls

- Label nằm trên input; helper text ở dưới label; lỗi ở ngay dưới input.
- Input nền Raised Slate, border Ledger Line, góc 10px, focus ring Signal Border.
- Multi-select analyst dùng hàng checkbox có mô tả ngắn, không dùng bốn card.
- Segmented control chỉ dùng cho lựa chọn ít và loại trừ nhau như research depth.
- Touch target tối thiểu 44px.

### Data rows and tables

- Hàng dữ liệu phân cách bằng border-top 1px; hover dùng Active Surface.
- Header bảng sticky khi bảng dài.
- Số căn phải bằng JetBrains Mono; chữ căn trái.
- Không dùng zebra stripe hoặc khung bao quanh từng ô.

### Decision marker

- Dùng một block chữ đậm, nhãn action và một vạch Verdigris dày 3px bên trái.
- BUY/HOLD/SELL không dùng badge hình pill và không dùng màu riêng.
- Có `aria-label` mô tả đầy đủ, không truyền đạt bằng màu đơn thuần.

### Agent status

- Agent là một hàng gọn gồm tên, vai trò, trạng thái và thời gian.
- Working: chấm Signal pulse opacity 0.45 → 1 trong 1.8 giây.
- Complete: dấu check outline tĩnh.
- Waiting: chấm rỗng Faint Alloy.
- Needs attention: biểu tượng cảnh báo Paper Ink và mô tả lỗi trực tiếp.

### Report sections

- Nội dung dài dùng max-width 72ch.
- Heading có anchor link xuất hiện khi hover hoặc focus.
- Trích dẫn dữ liệu dùng border-left Ledger Line, không dùng quote card.
- Chỉ dùng card/elevation cho decision summary và run summary, nơi cần thể hiện
  thứ bậc rõ ràng.

### Loading, empty and error states

- Loading dùng skeleton đúng kích thước nội dung sắp xuất hiện; shimmer rất nhẹ
  từ trái sang phải. Không dùng circular spinner.
- Empty state là một composition đơn giản mô tả năm bước phân tích và chỉ một
  hành động để bắt đầu.
- Lỗi API key, nguồn dữ liệu hoặc agent hiển thị inline tại đúng bước bị lỗi,
  giải thích bằng ngôn ngữ dễ hiểu và có hành động sửa cụ thể.
- Khi một báo cáo không được tạo, ghi rõ phần nào thiếu và lý do; không để vùng
  trắng im lặng.

## 7. Layout Principles

- Dùng CSS Grid cho bố cục chính. Không dùng phép tính phần trăm phức tạp.
- Container tối đa 1440px, căn giữa, padding ngang desktop 32px và mobile 16px.
- Không có phần tử nội dung chồng lên nhau hoặc absolute-positioned stacking.
- Không dùng bố cục ba card bằng nhau.
- Mọi màn hình dashboard dùng min-height `100dvh`, không dùng `100vh`.
- Nhịp spacing theo hệ 4px: 4, 8, 12, 16, 24, 32, 48, 64.
- Góc bo: 6px cho phần tử nhỏ, 10px cho control, 16px cho vùng nổi lớn. Không bo
  tròn quá mức.
- Shadow chỉ dùng khi cần tách decision summary hoặc sticky element khỏi nền.

## 8. Responsive Rules

- Dưới 768px, mọi bố cục nhiều cột chuyển thành một cột, không ngoại lệ.
- Không có horizontal scroll trên mobile, ngoại trừ vùng code hoặc bảng dữ liệu
  chuyên sâu có nhãn báo trước.
- Live analysis trên mobile ưu tiên `Current finding`; pipeline trở thành thanh
  tiến trình có thể mở rộng ở phía trên.
- Mục lục Full report trở thành nút `Report sections` sticky, mở sheet toàn chiều
  rộng.
- Bull và Bear xếp dọc; Risk debate giữ dạng tab với nhãn ngắn.
- Bảng Reports chuyển thành danh sách dọc, không ép người dùng kéo ngang.
- Tiêu đề dùng `clamp()`, body tối thiểu 1rem, tap target tối thiểu 44px.
- Khoảng cách dọc co theo `clamp(3rem, 8vw, 6rem)`.

## 9. Motion & Interaction

- Chuyển động mặc định theo spring: stiffness 100, damping 20.
- Danh sách agent và report section xuất hiện theo cascade 45-70ms khi lần đầu
  mount; không lặp lại khi người dùng quay lại tab.
- Agent đang Working là thành phần duy nhất có perpetual pulse. Không làm mọi
  thành phần hoạt ảnh liên tục trong màn hình dày dữ liệu.
- Skeleton shimmer và progress line chạy chậm, không nhấp nháy.
- Hover/focus transition 180-240ms; panel mở/đóng 260-320ms.
- Chỉ animate `transform` và `opacity`. Không animate `top`, `left`, `width`,
  `height`.
- Tôn trọng `prefers-reduced-motion`: bỏ pulse, cascade và shimmer; giữ thay đổi
  trạng thái tức thời nhưng rõ ràng.

## 10. Accessibility & Content Rules

- Tỷ lệ tương phản chữ đạt WCAG AA.
- Focus ring luôn thấy rõ bằng Signal Border 2px; mọi thao tác dùng được bằng bàn
  phím.
- Mọi biểu đồ có phần tóm tắt bằng chữ và bảng dữ liệu thay thế.
- Không truyền đạt BUY/HOLD/SELL, lỗi hoặc trạng thái chỉ bằng màu.
- Ngày hiển thị theo locale người dùng nhưng tooltip luôn có định dạng ISO
  `YYYY-MM-DD`.
- Giá và tiền tệ luôn ghi rõ đơn vị; không trộn USD và nội tệ mà không có nhãn.
- Dùng nội dung thật từ phiên phân tích. Không dùng lorem ipsum, tên công ty giả
  hoặc số liệu làm mẫu có vẻ như dữ liệu thật.
- Copy ngắn, trực tiếp: `Analysis paused. Resume from the last completed step.`
  thay vì thông báo chung chung.

## 11. Stitch Screen Generation Briefs

Khi tạo màn hình trong Stitch, dùng các mô tả sau cùng với toàn bộ design system
ở trên.

### Brief: Overview

Create a dense dark financial research workspace for TradingAgents. Use a slim
top navigation, an asymmetric left-aligned page header, one Verdigris primary
button, a full-width recent decisions table, a compact active-runs section, and a
quiet research-memory section. Make the newest decision easy to scan without
using green/red trading colors or equal card grids.

### Brief: New analysis

Create a two-column analysis setup screen. The wide left column contains asset,
research team, depth, and output controls. The narrow right column contains a
sticky run summary. Keep model/provider controls inside an advanced disclosure.
Use one primary Start analysis button and make the form approachable for a
non-technical investor.

### Brief: Live analysis

Create a high-density live research room with a narrow vertical five-stage agent
pipeline on the left and a wide current-finding reading surface on the right.
Show calm, precise progress, one slowly pulsing working agent, compact run stats,
and collapsed technical activity details. Do not imitate a terminal.

### Brief: Decision

Create an asymmetric investment decision screen where HOLD is the dominant
statement, followed by an executive summary, price target, stop loss, time
horizon, key reasons, and conditions that would change the decision. Include a
visible research-only disclaimer. Use Verdigris as the only accent and avoid
green/red buy-sell semantics.

### Brief: Full report

Create a long-form financial research report with a sticky section index, a wide
reading column, sequential analyst sections, a side-by-side Bull versus Bear
comparison, tabbed risk perspectives, anchored evidence markers, and a sticky
mini decision summary. Prioritize reading comfort despite high information
density.

### Brief: Reports

Create a searchable report history screen centered on a sortable data table,
with ticker, asset type, analysis date, decision, target, horizon, completion
time, and report status. Rows expand inline to reveal executive summaries.
Avoid a card gallery.

## 12. Anti-Patterns: Never Do

- Không dùng emoji trong giao diện.
- Không dùng font Inter hoặc generic serif.
- Không dùng pure black `#000000`.
- Không dùng purple/blue AI gradient, neon hoặc outer glow.
- Không dùng nhiều hơn một màu nhấn.
- Không dùng màu xanh/đỏ để thúc đẩy quyết định BUY/SELL.
- Không dùng ba card bằng nhau theo hàng ngang.
- Không dùng sidebar cố định mặc định.
- Không tạo dashboard từ hàng loạt card có border + shadow giống nhau.
- Không dùng hero căn giữa hoặc headline khổng lồ trong màn hình phần mềm.
- Không overlap nội dung, text hoặc ảnh.
- Không dùng terminal giả làm giao diện chính.
- Không hiển thị tool calls và token trước nội dung người dùng cần hiểu.
- Không dùng modal cho tác vụ đơn giản có thể làm inline.
- Không dùng circular spinner.
- Không dùng custom mouse cursor.
- Không dùng filler copy, lorem ipsum, generic names hoặc số liệu giả tròn trịa.
- Không dùng các cụm từ sáo rỗng như "Elevate", "Seamless", "Unleash",
  "Next-Gen".
- Không dùng scroll arrows, bouncing chevrons hoặc "Scroll to explore".
- Không animate thuộc tính gây layout shift.
- Không che giấu disclaimer nghiên cứu hoặc làm nó khó đọc.
