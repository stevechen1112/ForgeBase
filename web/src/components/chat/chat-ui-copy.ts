export type ChatUiCopy = {
  rfqReady: string;
  rfqReadyDescription: string;
  prepareRfq: string;
  relatedSource: string;
  thinking: string;
  placeholder: string;
  sendMessage: string;
};

const copies: Record<string, ChatUiCopy> = {
  en: { rfqReady: "RFQ Ready", rfqReadyDescription: "Your request is specific enough to continue with a prefilled RFQ.", prepareRfq: "Prepare RFQ", relatedSource: "Related source", thinking: "Thinking...", placeholder: "Ask about material, MOQ, OEM, or certification...", sendMessage: "Send message" },
  zh: { rfqReady: "可進入詢價", rfqReadyDescription: "您的需求已足夠明確，可以帶入預填資料繼續詢價。", prepareRfq: "準備 RFQ", relatedSource: "相關資料", thinking: "思考中...", placeholder: "可詢問材質、MOQ、OEM、認證或包裝需求...", sendMessage: "送出訊息" },
  ja: { rfqReady: "見積依頼の準備完了", rfqReadyDescription: "ご要望が明確になりました。入力済みの内容で見積依頼に進めます。", prepareRfq: "RFQを作成", relatedSource: "関連資料", thinking: "回答を作成中...", placeholder: "材質、MOQ、OEM、認証についてご質問ください...", sendMessage: "メッセージを送信" },
  ko: { rfqReady: "견적 요청 준비 완료", rfqReadyDescription: "요청 사항이 충분히 구체적입니다. 미리 입력된 내용으로 견적 요청을 계속할 수 있습니다.", prepareRfq: "RFQ 준비", relatedSource: "관련 자료", thinking: "답변 작성 중...", placeholder: "소재, MOQ, OEM 또는 인증에 대해 질문해 주세요...", sendMessage: "메시지 보내기" },
  de: { rfqReady: "Anfrage bereit", rfqReadyDescription: "Ihre Anforderungen sind konkret genug, um mit einer vorausgefüllten Anfrage fortzufahren.", prepareRfq: "Anfrage vorbereiten", relatedSource: "Relevante Quelle", thinking: "Antwort wird erstellt...", placeholder: "Fragen Sie nach Material, MOQ, OEM oder Zertifizierung...", sendMessage: "Nachricht senden" },
  fr: { rfqReady: "Demande de devis prête", rfqReadyDescription: "Votre besoin est assez précis pour poursuivre avec une demande de devis préremplie.", prepareRfq: "Préparer la demande", relatedSource: "Source associée", thinking: "Préparation de la réponse...", placeholder: "Posez une question sur le matériau, le MOQ, l’OEM ou la certification...", sendMessage: "Envoyer le message" },
  es: { rfqReady: "Solicitud de cotización lista", rfqReadyDescription: "Su solicitud es suficientemente específica para continuar con un formulario de cotización prellenado.", prepareRfq: "Preparar solicitud", relatedSource: "Fuente relacionada", thinking: "Preparando respuesta...", placeholder: "Pregunte sobre material, MOQ, OEM o certificación...", sendMessage: "Enviar mensaje" },
  it: { rfqReady: "Richiesta di preventivo pronta", rfqReadyDescription: "La richiesta è abbastanza specifica per continuare con un modulo precompilato.", prepareRfq: "Prepara richiesta", relatedSource: "Fonte correlata", thinking: "Preparazione della risposta...", placeholder: "Chiedi informazioni su materiali, MOQ, OEM o certificazioni...", sendMessage: "Invia messaggio" },
  pt: { rfqReady: "Pedido de cotação pronto", rfqReadyDescription: "O seu pedido está suficientemente detalhado para continuar com um formulário pré-preenchido.", prepareRfq: "Preparar cotação", relatedSource: "Fonte relacionada", thinking: "A preparar resposta...", placeholder: "Pergunte sobre material, MOQ, OEM ou certificação...", sendMessage: "Enviar mensagem" },
  nl: { rfqReady: "Offerteaanvraag gereed", rfqReadyDescription: "Uw aanvraag is specifiek genoeg om door te gaan met een vooraf ingevuld formulier.", prepareRfq: "Aanvraag voorbereiden", relatedSource: "Gerelateerde bron", thinking: "Antwoord wordt opgesteld...", placeholder: "Vraag naar materiaal, MOQ, OEM of certificering...", sendMessage: "Bericht verzenden" },
  pl: { rfqReady: "Zapytanie ofertowe gotowe", rfqReadyDescription: "Wymagania są wystarczająco szczegółowe, aby przejść do wstępnie wypełnionego zapytania.", prepareRfq: "Przygotuj zapytanie", relatedSource: "Powiązane źródło", thinking: "Przygotowywanie odpowiedzi...", placeholder: "Zapytaj o materiał, MOQ, OEM lub certyfikację...", sendMessage: "Wyślij wiadomość" },
  ru: { rfqReady: "Запрос предложения готов", rfqReadyDescription: "Ваш запрос достаточно конкретен, чтобы перейти к предварительно заполненной форме.", prepareRfq: "Подготовить запрос", relatedSource: "Связанный источник", thinking: "Подготовка ответа...", placeholder: "Спросите о материале, MOQ, OEM или сертификации...", sendMessage: "Отправить сообщение" },
  uk: { rfqReady: "Запит пропозиції готовий", rfqReadyDescription: "Ваш запит достатньо конкретний, щоб перейти до попередньо заповненої форми.", prepareRfq: "Підготувати запит", relatedSource: "Пов’язане джерело", thinking: "Підготовка відповіді...", placeholder: "Запитайте про матеріал, MOQ, OEM або сертифікацію...", sendMessage: "Надіслати повідомлення" },
  tr: { rfqReady: "Teklif talebi hazır", rfqReadyDescription: "Talebiniz, önceden doldurulmuş teklif formuyla devam etmek için yeterince ayrıntılı.", prepareRfq: "Teklif talebi hazırla", relatedSource: "İlgili kaynak", thinking: "Yanıt hazırlanıyor...", placeholder: "Malzeme, MOQ, OEM veya sertifika hakkında sorun...", sendMessage: "Mesaj gönder" },
  ar: { rfqReady: "طلب عرض السعر جاهز", rfqReadyDescription: "طلبك محدد بما يكفي للمتابعة باستخدام نموذج عرض سعر مُعبأ مسبقاً.", prepareRfq: "إعداد طلب السعر", relatedSource: "مصدر ذو صلة", thinking: "جارٍ إعداد الرد...", placeholder: "اسأل عن المواد أو الحد الأدنى للطلب أو OEM أو الشهادات...", sendMessage: "إرسال الرسالة" },
  he: { rfqReady: "בקשת הצעת המחיר מוכנה", rfqReadyDescription: "הבקשה מפורטת מספיק כדי להמשיך לטופס שמולא מראש.", prepareRfq: "הכנת בקשה", relatedSource: "מקור קשור", thinking: "מכין תשובה...", placeholder: "אפשר לשאול על חומר, MOQ, OEM או הסמכה...", sendMessage: "שליחת הודעה" },
  th: { rfqReady: "พร้อมขอใบเสนอราคา", rfqReadyDescription: "คำขอของคุณชัดเจนเพียงพอที่จะดำเนินการต่อด้วยแบบฟอร์มที่กรอกข้อมูลไว้แล้ว", prepareRfq: "เตรียม RFQ", relatedSource: "ข้อมูลที่เกี่ยวข้อง", thinking: "กำลังเตรียมคำตอบ...", placeholder: "สอบถามเรื่องวัสดุ MOQ OEM หรือการรับรอง...", sendMessage: "ส่งข้อความ" },
  vi: { rfqReady: "Yêu cầu báo giá đã sẵn sàng", rfqReadyDescription: "Yêu cầu của bạn đã đủ cụ thể để tiếp tục với biểu mẫu được điền sẵn.", prepareRfq: "Chuẩn bị RFQ", relatedSource: "Nguồn liên quan", thinking: "Đang chuẩn bị câu trả lời...", placeholder: "Hỏi về vật liệu, MOQ, OEM hoặc chứng nhận...", sendMessage: "Gửi tin nhắn" },
  id: { rfqReady: "Permintaan penawaran siap", rfqReadyDescription: "Permintaan Anda cukup spesifik untuk dilanjutkan dengan formulir yang telah diisi.", prepareRfq: "Siapkan RFQ", relatedSource: "Sumber terkait", thinking: "Menyiapkan jawaban...", placeholder: "Tanyakan tentang bahan, MOQ, OEM, atau sertifikasi...", sendMessage: "Kirim pesan" },
  ms: { rfqReady: "Permintaan sebut harga sedia", rfqReadyDescription: "Permintaan anda cukup khusus untuk diteruskan dengan borang yang telah diisi.", prepareRfq: "Sediakan RFQ", relatedSource: "Sumber berkaitan", thinking: "Menyediakan jawapan...", placeholder: "Tanya tentang bahan, MOQ, OEM atau pensijilan...", sendMessage: "Hantar mesej" },
  hi: { rfqReady: "कोटेशन अनुरोध तैयार है", rfqReadyDescription: "आपकी आवश्यकता पहले से भरे RFQ के साथ आगे बढ़ने के लिए पर्याप्त स्पष्ट है।", prepareRfq: "RFQ तैयार करें", relatedSource: "संबंधित स्रोत", thinking: "उत्तर तैयार किया जा रहा है...", placeholder: "सामग्री, MOQ, OEM या प्रमाणन के बारे में पूछें...", sendMessage: "संदेश भेजें" },
  el: { rfqReady: "Το αίτημα προσφοράς είναι έτοιμο", rfqReadyDescription: "Το αίτημά σας είναι αρκετά συγκεκριμένο για να συνεχίσετε με προσυμπληρωμένη φόρμα.", prepareRfq: "Προετοιμασία αιτήματος", relatedSource: "Σχετική πηγή", thinking: "Προετοιμασία απάντησης...", placeholder: "Ρωτήστε για υλικό, MOQ, OEM ή πιστοποίηση...", sendMessage: "Αποστολή μηνύματος" },
  sv: { rfqReady: "Offertförfrågan klar", rfqReadyDescription: "Din förfrågan är tillräckligt tydlig för att fortsätta med ett förifyllt formulär.", prepareRfq: "Förbered förfrågan", relatedSource: "Relaterad källa", thinking: "Förbereder svar...", placeholder: "Fråga om material, MOQ, OEM eller certifiering...", sendMessage: "Skicka meddelande" },
  da: { rfqReady: "Tilbudsforespørgsel klar", rfqReadyDescription: "Din forespørgsel er konkret nok til at fortsætte med en forhåndsudfyldt formular.", prepareRfq: "Forbered forespørgsel", relatedSource: "Relateret kilde", thinking: "Forbereder svar...", placeholder: "Spørg om materiale, MOQ, OEM eller certificering...", sendMessage: "Send besked" },
  no: { rfqReady: "Tilbudsforespørsel klar", rfqReadyDescription: "Forespørselen er konkret nok til å fortsette med et forhåndsutfylt skjema.", prepareRfq: "Forbered forespørsel", relatedSource: "Relatert kilde", thinking: "Forbereder svar...", placeholder: "Spør om materiale, MOQ, OEM eller sertifisering...", sendMessage: "Send melding" },
  fi: { rfqReady: "Tarjouspyyntö valmis", rfqReadyDescription: "Pyyntösi on riittävän tarkka jatkaaksesi esitäytetyllä lomakkeella.", prepareRfq: "Valmistele tarjouspyyntö", relatedSource: "Liittyvä lähde", thinking: "Valmistellaan vastausta...", placeholder: "Kysy materiaalista, MOQ:sta, OEM:stä tai sertifioinnista...", sendMessage: "Lähetä viesti" },
  cs: { rfqReady: "Poptávka je připravena", rfqReadyDescription: "Váš požadavek je dostatečně konkrétní pro pokračování s předvyplněným formulářem.", prepareRfq: "Připravit poptávku", relatedSource: "Související zdroj", thinking: "Připravuji odpověď...", placeholder: "Zeptejte se na materiál, MOQ, OEM nebo certifikaci...", sendMessage: "Odeslat zprávu" },
  hu: { rfqReady: "Ajánlatkérés kész", rfqReadyDescription: "A kérése elég részletes ahhoz, hogy előre kitöltött űrlappal folytassa.", prepareRfq: "Ajánlatkérés előkészítése", relatedSource: "Kapcsolódó forrás", thinking: "Válasz készítése...", placeholder: "Kérdezzen az anyagról, MOQ-ról, OEM-ről vagy tanúsításról...", sendMessage: "Üzenet küldése" },
  ro: { rfqReady: "Cererea de ofertă este pregătită", rfqReadyDescription: "Solicitarea este suficient de clară pentru a continua cu un formular precompletat.", prepareRfq: "Pregătește cererea", relatedSource: "Sursă asociată", thinking: "Se pregătește răspunsul...", placeholder: "Întrebați despre material, MOQ, OEM sau certificare...", sendMessage: "Trimite mesajul" },
};

export function chatLanguage(locale?: string): string {
  const normalized = (locale || "en").trim().toLowerCase().replace("_", "-");
  return normalized.startsWith("zh") ? "zh" : normalized.split("-")[0];
}

export function getChatUiCopy(locale?: string): ChatUiCopy {
  return copies[chatLanguage(locale)] || copies.en;
}

export function chatDirection(locale?: string): "ltr" | "rtl" {
  return ["ar", "he", "fa", "ur"].includes(chatLanguage(locale)) ? "rtl" : "ltr";
}
