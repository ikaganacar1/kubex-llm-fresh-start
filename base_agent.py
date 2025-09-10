from abc import ABC, abstractmethod
from typing import Dict, Any, List, Generator, Union, Optional 
import json

class BaseAgent(ABC):
    """Tüm ajanlar için temel sınıf - İyileştirilmiş memory ve context yönetimi ile"""
    
    def __init__(self, client, category: str, description: str, manager: Optional[Any] = None):
        self.client = client
        self.category = category
        self.description = description
        self.manager = manager  # AgentManager referansını sakla
        self.waiting_for_parameters = False
        self.current_tool_context = None
        self.last_user_request = None
        self.conversation_context = []
    
    @abstractmethod
    def get_tools(self) -> Dict[str, Any]:
        """Agent'in kullanabileceği araçları döndürür"""
        pass
    
    @abstractmethod
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any], original_request: str = None) -> Generator[str, None, None]:
        """Belirtilen aracı çalıştırır"""
        pass
    
    def get_system_prompt(self) -> str:
        """Agent için system prompt oluşturur"""
        tools_description_lines = []
        tools_dict = self.get_tools()

        for name, details in tools_dict.items():
            param_list = []
            for p in details.get("parameters", []):
                param_name = p.get('name', 'param')
                # Otomatik enjekte edilen parametreleri prompt'ta gizle veya işaretle
                if param_name != "cluster_id":
                    param_list.append(f"{param_name} ({p.get('in', 'N/A')})")

            params_str = ", ".join(param_list) if param_list else "Yok"
            tools_description_lines.append(
                f"- Arac Adi: '{name}'\n"
                f"  - Aciklama: {details.get('summary', '')}\n"
                f"  - Gerekli Parametreler: {params_str}"
            )
        tools_prompt = "\n".join(tools_description_lines)

        context_info = ""
        if self.conversation_context:
            context_info = f"\n\n### SON SOHBET OZETI ###\n{self._get_conversation_summary()}\n"

        # --- YENİ İYİLEŞTİRİLMİŞ PROMPT ---
        return (
            f"### ROL VE UZMANLIK ALANI ###\n"
            f"Sen {self.category} konusunda uzman bir asistansın. Görevin, kullanıcının isteğini analiz etmek, "
            f"bu isteği gerçekleştirmek için aşağıdaki araçlardan en uygun olanını seçmek ve çalıştırmak için gerekli tüm parametreleri toplamaktır.\n\n"
            f"### ARAÇ SETİ ({self.category}) ###\n{tools_prompt}\n\n"
            f"{context_info}"
            "### BAĞLAM VE PARAMETRE YÖNETİMİ KURALLARI ###\n"
            "1. **Öncelikli Görev: Eksik Parametre Toplama:**\n"
            "   - Eğer bir araç seçilmişse (`waiting_for_parameters = True`) ve parametreleri eksikse, TARTIŞMASIZ önceliğin bu eksik parametreleri kullanıcıdan istemektir.\n"
            "   - Kullanıcının yeni mesajını, bu eksik parametreleri doldurmak için bir yanıt olarak yorumla.\n"
            "   - Ancak, kullanıcı yeni mesajında açıkça ve tamamen farklı bir konuya geçerse, bu kuralı devre dışı bırak ve yeni isteği analiz et.\n"
            "2. **Otomatik Bağlam Enjeksiyonu (ÇOK ÖNEMLİ):**\n"
            "   - `cluster_id` parametresi, sistem tarafından global bağlamdan otomatik olarak sağlanmaktadır.\n"
            "   - Kullanıcıya `cluster_id` Sorma. Sadece diğer (örn: `namespace`, `deployment_name`) eksik parametrelere odaklan.\n"
            "3. **Sohbet Modu:** Eğer kullanıcının isteği listedeki araçlarla gerçekleştirilemiyorsa veya kullanıcı sadece sohbet etmek istiyorsa, `tool_name: \"chat\"` kullan.\n\n"
            "### ÇIKIŞ FORMATI ###\n"
            "Analiz sonucunda YALNIZCA bir JSON objesi döndür:\n\n"
            "1. Arac Kullanimi:\n"
            '{"tool_name": "kullanilacak_arac_adi", "parameters": {"parametre_adi": "deger"}}\n\n'
            "2. Sohbet/Yanit:\n"
            '{"tool_name": "chat", "parameters": {"response": "kullaniciya_verilecek_cevap"}}\n\n'
            "Yanitinda JSON objesi disinda KESINLIKLE hicbir metin veya aciklama olmasin."
        )
    def reset_context(self):
        """Bağlamı sıfırla"""
        self.waiting_for_parameters = False
        self.current_tool_context = None
        # YENI: Tam reset yapmak yerine conversation_context'i koru
        # self.conversation_context = []  # Bunu kaldırdık
        self.last_user_request = None
    
    def add_to_conversation_context(self, user_message: str, assistant_response: str):
        """YENI: Conversation context'e yeni etkileşim ekle"""
        self.conversation_context.append({
            "user": user_message,
            "assistant": assistant_response,
            "timestamp": "recent"
        })
        
        # Memory limitini koru (son 5 etkileşim)
        if len(self.conversation_context) > 5:
            self.conversation_context = self.conversation_context[-5:]
    
    def _get_conversation_summary(self) -> str:
        """YENI: Conversation context'in özetini döndür"""
        if not self.conversation_context:
            return "Henuz bir sohbet gecmisi yok."
            
        summary_parts = []
        for i, interaction in enumerate(self.conversation_context[-3:], 1):  # Son 3 etkileşim
            user_msg = interaction["user"][:100] + "..." if len(interaction["user"]) > 100 else interaction["user"]
            assistant_msg = interaction["assistant"][:100] + "..." if len(interaction["assistant"]) > 100 else interaction["assistant"]
            summary_parts.append(f"{i}. Kullanici: {user_msg}\n   Asistan: {assistant_msg}")
        
        return "\n".join(summary_parts)
    
    def process_request(self, prompt: str) -> Union[Dict[str, Any], Generator[str, None, None]]:
        """İsteği işle - iyileştirilmiş memory management ve otomatik enjeksiyon ile"""
        print(f"[{self.category}] İstek işleniyor: {prompt}")
        
        self.last_user_request = prompt
        
        llm_decision = self._call_llm_for_tool_selection(prompt, use_history=True)
        tool_name = llm_decision.get("tool_name")
        parameters = llm_decision.get("parameters", {})
        
        if not tool_name or tool_name == "chat":
            response_text = parameters.get("response", f"{self.category} ile ilgili size nasil yardimci olabilirim?")
            self.waiting_for_parameters = False
            self.current_tool_context = None
            self.add_to_conversation_context(prompt, response_text)
            
            def stream_response():
                yield response_text
            return stream_response()

        tools_dict = self.get_tools()
        tool_info = tools_dict.get(tool_name)
        
        if not tool_info:
            print(f"[{self.category}] LLM var olmayan bir araç seçti: {tool_name}")
            self.waiting_for_parameters = False
            self.current_tool_context = None
            return self._create_error_response(f"'{tool_name}' adinda bir arac bulunamadi.")

        # --- YENİ EKLENTİ: Otomatik Cluster ID Enjeksiyonu ---
        # 1. Agent'ın manager'a erişimi var mı diye kontrol et (constructor'da enjekte edilmeli)
        if hasattr(self, 'manager') and self.manager:
            # 2. Seçilen aracın 'cluster_id' parametresine ihtiyacı var mı?
            tool_requires_cluster_id = False
            for param_def in tool_info.get("parameters", []):
                if param_def.get("name") == "cluster_id":
                    tool_requires_cluster_id = True
                    break
            
            # 3. Eğer LLM cluster_id'yi sağlamadıysa ve araç buna ihtiyaç duyuyorsa, global state'den enjekte et.
            if tool_requires_cluster_id and "cluster_id" not in parameters:
                contextual_params = self.manager.get_contextual_parameters()
                if contextual_params.get("cluster_id"):
                    parameters["cluster_id"] = contextual_params["cluster_id"]
                    print(f"[{self.category}] Otomatik enjeksiyon: cluster_id={contextual_params['cluster_id']} araca eklendi.")
        # --- ENJEKSİYON BİTİŞİ ---

        # Eksik parametre kontrolü (enjeksiyon sonrasında yapılır)
        missing_params = []
        for required_param in tool_info.get("parameters", []):
            if required_param.get("required") and required_param.get("name") not in parameters:
                missing_params.append(required_param.get("name"))

        if missing_params:
            print(f"[{self.category}] Eksik parametreler tespit edildi: {missing_params}")
            
            self.waiting_for_parameters = True
            self.current_tool_context = {
                "tool_name": tool_name,
                "missing_params": missing_params,
                "extracted_params": parameters,
                "original_request": prompt
            }
            
            return {
                "status": "needs_parameters",
                "tool_name": tool_name,
                "missing_params": missing_params,
                "questions": [f"Lutfen '{p}' degeri icin bilgi verin:" for p in missing_params],
                "extracted_params": parameters
            }

        self.waiting_for_parameters = False
        self.current_tool_context = None
        return self.execute_tool(tool_name, parameters, original_request=prompt)

    def finalize_request(self, tool_name: str, extracted_params: dict, collected_params: dict) -> Generator[str, None, None]:
        """Parametre toplama tamamlandıktan sonra aracı çalıştır - iyileştirilmiş context ile"""
        all_params = {**extracted_params, **collected_params}
        self.waiting_for_parameters = False

        # --- DEBUG LOGGING BAŞLANGICI ---
        original_request = "Original request context not found"
        if self.current_tool_context:
            original_request = self.current_tool_context.get("original_request", "Original request key missing")
        
        print(f"[{self.category}] Finalizing tool execution.")
        print(f"[{self.category}] Tool Name: {tool_name}")
        print(f"[{self.category}] All Parameters for execution: {all_params}")
        print(f"[{self.category}] Original Request context: {original_request}")
        # --- DEBUG LOGGING BİTİŞİ ---
            
        self.current_tool_context = None
        return self.execute_tool(tool_name, all_params, original_request=original_request)
    
    def _call_llm_for_tool_selection(self, prompt: str, use_history: bool = True) -> Dict[str, Any]:
        """LLM'den araç seçimi iste - iyileştirilmiş context ile"""
        try:
            if self.waiting_for_parameters and self.current_tool_context and use_history:
                context_reminder = (
                    f"BAGLAM: Daha once '{self.current_tool_context['tool_name']}' aracini sectim. "
                    f"Eksik parametreler: {', '.join(self.current_tool_context['missing_params'])}. "
                    f"ORIJINAL ISTEK: {self.current_tool_context.get('original_request', 'bilinmiyor')}\n"
                    f"Kullanicinin yeni mesaji bu parametreleri saglamaya yonelik olmali.\n\n"
                    f"Kullanici mesaji: {prompt}"
                )
                response = self.client.chat(user_prompt=context_reminder, system_prompt=self.get_system_prompt(), use_history=True)
            else:
                response = self.client.chat(user_prompt=prompt, system_prompt=self.get_system_prompt(), use_history=use_history)
            
            content = response.get("message", {}).get("content", "{}")
            first_brace_index = content.find('{')
            if first_brace_index == -1:
                raise ValueError("JSON bulunamadı")
            json_str_with_trailing_junk = content[first_brace_index:]
            
            decoded_json, _ = json.JSONDecoder().raw_decode(json_str_with_trailing_junk)
            return decoded_json
        except Exception as e:
            print(f"[{self.category}] LLM'den geçerli JSON alınamadı: {e}")
            return {"tool_name": "chat", "parameters": {"response": "Ne istediginizi anlayamadim, lutfen daha net bir sekilde ifade eder misiniz?"}}
    
    def _create_error_response(self, error_message: str) -> Generator[str, None, None]:
        """Hata yanıtı oluştur"""
        # YENI: Error'u da context'e ekle
        if self.last_user_request:
            self.add_to_conversation_context(self.last_user_request, error_message)
            
        def stream_response():
            yield error_message
        return stream_response()
    
    def _summarize_result_for_user(self, result: Any, original_request: str = None) -> Generator[str, None, None]:
        """YENI: Araç sonucunu kullanıcı için özetle - orijinal istek ile birlikte"""

        if not original_request:
            original_request = self.last_user_request or "Bilinmeyen istek"

        json_data = json.dumps(result, indent=2, ensure_ascii=False)

        # --- YENİ İYİLEŞTİRİLMİŞ PROMPT ---
        summary_prompt = (
            "### GÖREV VE PERSONA ###\n"
            "Senin görevin, bir Kubernetes API aracından gelen teknik JSON verisini analiz etmek ve sonucu kullanıcıya sunmaktır. "
            "Sen, teknik bilgiyi basitleştiren, kullanıcı dostu ve proaktif bir tercümansın.\n\n"
            "### TALİMATLAR ###\n"
            "1. **Bağlamı Koru:** Kullanıcının orijinal isteğini (`ORIJINAL KULLANICI ISTEGI`) dikkate alarak yanıt ver. "
            "Yanıtın, kullanıcının sorusuna doğrudan cevap olduğundan emin ol.\n"
            "2. **Başarı Durumu Yorumlama:**\n"
            "   - Eğer işlem başarılıysa (`status: success`) ve sonuç bir liste ise, listenin içeriğini özetle. "
            "Eğer liste boşsa (`count: 0` veya `[]`), \"İlgili kriterlere uygun kaynak bulunamadı.\" gibi net bir ifade kullan.\n"
            "   - Eğer işlem bir yaratma/silme/güncelleme ise, işlemin başarıyla tamamlandığını teyit et.\n"
            "3. **Hata Durumu Yorumlama (Proaktif Yaklaşım):**\n"
            "   - Eğer işlem başarısızsa (`status: error`), hatayı sadece aktarma. Hatayı kullanıcı diline çevir.\n"
            "   - Hata mesajına dayanarak olası nedeni tahmin et (örn: \"Resource not found\" -> \"Belirttiğiniz isimde bir kaynak bulunamadı.\").\n"
            "   - Kullanıcıya bir sonraki adımda neyi kontrol etmesi gerektiğine dair bir öneride bulun (örn: \"Lütfen yazdığınız ismi kontrol edin veya kaynağın doğru namespace'de olduğundan emin olun.\").\n\n"
            "### VERİLER ###\n"
            f"**ORIJINAL KULLANICI ISTEGI:** {original_request}\n\n"
            f"**İŞLENECEK TEKNİK JSON VERİSİ:**\n{json_data}\n\n"
            f"### ÇIKIŞ ###\nYukarıdaki talimatlara göre oluşturulmuş, akıcı ve doğal dilde (Türkçe) yanıtı üret."
        )

        print(f"[{self.category}] Araç sonucu için LLM'den özet isteniyor (orijinal istek: {original_request[:50]}...)")

        response_generator = self.client.chat_stream(
            user_prompt=summary_prompt,
            use_history=True # Bağlamı korumak için sohbet geçmişini kullan
        )
        
        # Response'u collect et ve context'e ekle
        full_response = ""
        for chunk in response_generator:
            full_response += chunk
            yield chunk
            
        if original_request:
            self.add_to_conversation_context(original_request, full_response)