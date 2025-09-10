# llm_services/summarizer_llm_service.py

import json
from typing import Any, Generator

class SummarizerLLMService:
    """
    Araçların teknik çıktılarını kullanıcı dostu bir dilde özetlemekle sorumlu LLM servisi.
    """
    def __init__(self, client: Any):
        self.client = client

    def _build_summary_prompt(self, tool_result: Any, original_request: str) -> str:
        """Özetleme LLM'i için sistem komutunu oluşturur."""
        json_data = json.dumps(tool_result, indent=2, ensure_ascii=False)

        return (
            "### GÖREV VE PERSONA ###\n"
            "Senin görevin, bir API aracından gelen teknik JSON verisini analiz etmek ve sonucu kullanıcıya sunmaktır. "
            "Sen, teknik bilgiyi basitleştiren, kullanıcı dostu ve proaktif bir tercümansın.\n\n"
            "### TALİMATLAR ###\n"
            "1. **Bağlamı Koru:** Kullanıcının orijinal isteğini (`ORIJINAL KULLANICI ISTEGI`) dikkate alarak yanıt ver.\n"
            "2. **Başarı Durumu Yorumlama:** Eğer işlem başarılıysa (`status: success`), sonucu özetle. Liste boşsa bunu netçe belirt.\n"
            "3. **Hata Durumu Yorumlama (Proaktif Yaklaşım):** Eğer işlem başarısızsa (`status: error`), hatayı kullanıcı diline çevir, olası nedeni tahmin et ve bir sonraki adım için öneride bulun.\n\n"
            "### VERİLER ###\n"
            f"**ORIJINAL KULLANICI ISTEGI:** {original_request}\n\n"
            f"**İŞLENECEK TEKNİK JSON VERİSİ:**\n{json_data}\n\n"
            f"### ÇIKIŞ ###\nYukarıdaki talimatlara göre oluşturulmuş, akıcı ve doğal dilde (Türkçe) yanıtı üret."
        )

    def summarize_stream(self, tool_result: Any, original_request: str, agent_category: str) -> Generator[str, None, None]:
        """LLM'den bir araç sonucunu akış olarak özetlemesini ister."""
        summary_prompt = self._build_summary_prompt(tool_result, original_request)
        
        print(f"[{agent_category}] Araç sonucu için LLM'den özet isteniyor (orijinal istek: {original_request[:50]}...)")

        # chat_stream metodu doğrudan user_prompt'u işler, system_prompt ayrı bir parametre olarak verilmeyebilir
        # Bu yüzden tüm prompt'u tek bir string olarak gönderiyoruz.
        # Eğer client'ınız system ve user prompt'ları ayrı alıyorsa, ona göre düzenleyin.
        response_generator = self.client.chat_stream(
            user_prompt=summary_prompt,
            use_history=True 
        )
        
        yield from response_generator