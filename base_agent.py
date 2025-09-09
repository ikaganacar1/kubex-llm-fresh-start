from abc import ABC, abstractmethod
from typing import Dict, Any, List, Generator, Union
import logging

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Tüm ajanlar için temel sınıf"""
    
    def __init__(self, client, category: str, description: str):
        self.client = client
        self.category = category
        self.description = description
        self.waiting_for_parameters = False
        self.current_tool_context = None
    
    @abstractmethod
    def get_tools(self) -> Dict[str, Any]:
        """Agent'in kullanabileceği araçları döndürür"""
        pass
    
    @abstractmethod
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Generator[str, None, None]:
        """Belirtilen aracı çalıştırır"""
        pass
    
    def get_system_prompt(self) -> str:
        """Agent için system prompt oluşturur"""
        tools_description_lines = [f"Bu kategorideki ({self.category}) islemleri icin asagidaki araclardan birini secebilirsin:"]
        tools_dict = self.get_tools()
        
        for name, details in tools_dict.items():
            param_list = [f"{p.get('name', 'param')} ({p.get('in', 'N/A')})" for p in details.get("parameters", [])]
            params_str = ", ".join(param_list) if param_list else "Yok"
            tools_description_lines.append(
                f"- Arac Adi: '{name}'\n"
                f"  - Aciklama: {details.get('summary', '')}\n"
                f"  - Gerekli Parametreler: {params_str}"
            )
        tools_prompt = "\n".join(tools_description_lines)

        return (
            f"Sen {self.category} uzmanı bir asistansın. {self.description}\n\n"
            f"{tools_prompt}\n\n"
            "ONEMLI KURALLAR:\n"
            "1. Eger daha once bir arac sectin ve parametreler eksikse, kullanicinin yeni mesajlarini "
            "o aracin eksik parametrelerini tamamlamak icin kullan.\n"
            "2. Kullanici tamamen farkli bir konu actiginda yeni bir arac sec veya sohbet et.\n"
            "3. Parametre toplama sirasinda kullaniciya sabir goster ve eksik bilgileri net sor.\n\n"
            "Kullanicinin istegini analiz ettikten sonra, YALNIZCA bir JSON objesi dondur:\n\n"
            "1. Arac kullanacaksan:\n"
            '{"tool_name": "kullanilacak_arac_adi", "parameters": {"parametre_adi": "deger"}}\n\n'
            "2. Sohbet edeceksen:\n"
            '{"tool_name": "chat", "parameters": {"response": "kullaniciya_verilecek_cevap"}}\n\n'
            "Yanitinda JSON objesi disinda KESINLIKLE hicbir metin, aciklama veya formatlama isareti olmasin."
        )
    
    def reset_context(self):
        """Bağlamı sıfırla"""
        self.waiting_for_parameters = False
        self.current_tool_context = None
    
    def process_request(self, prompt: str) -> Union[Dict[str, Any], Generator[str, None, None]]:
        """İsteği işle - temel mantık"""
        logger.info(f"[{self.category}] İstek işleniyor: {prompt}")
        
        llm_decision = self._call_llm_for_tool_selection(prompt, use_history=True)
        tool_name = llm_decision.get("tool_name")
        parameters = llm_decision.get("parameters", {})

        if not tool_name or tool_name == "chat":
            response_text = parameters.get("response", f"{self.category} ile ilgili size nasil yardimci olabilirim?")
            self.waiting_for_parameters = False
            self.current_tool_context = None
            def stream_response():
                yield response_text
            return stream_response()

        tools_dict = self.get_tools()
        tool_info = tools_dict.get(tool_name)
        
        if not tool_info:
            logger.warning(f"[{self.category}] LLM var olmayan bir araç seçti: {tool_name}")
            self.waiting_for_parameters = False
            self.current_tool_context = None
            return self._create_error_response(f"'{tool_name}' adinda bir arac bulunamadi.")

        missing_params = []
        for required_param in tool_info.get("parameters", []):
            if required_param.get("required") and required_param.get("name") not in parameters:
                missing_params.append(required_param.get("name"))

        if missing_params:
            logger.info(f"[{self.category}] Eksik parametreler tespit edildi: {missing_params}")
            
            self.waiting_for_parameters = True
            self.current_tool_context = {
                "tool_name": tool_name,
                "missing_params": missing_params,
                "extracted_params": parameters
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
        return self.execute_tool(tool_name, parameters)

    def finalize_request(self, tool_name: str, extracted_params: dict, collected_params: dict) -> Generator[str, None, None]:
        """Parametre toplama tamamlandıktan sonra aracı çalıştır"""
        all_params = {**extracted_params, **collected_params}
        self.waiting_for_parameters = False
        self.current_tool_context = None
        return self.execute_tool(tool_name, all_params)
    
    def _call_llm_for_tool_selection(self, prompt: str, use_history: bool = True) -> Dict[str, Any]:
        """LLM'den araç seçimi iste"""
        try:
            if self.waiting_for_parameters and self.current_tool_context and use_history:
                context_reminder = (
                    f"BAGLAM: Daha once '{self.current_tool_context['tool_name']}' aracini sectim. "
                    f"Eksik parametreler: {', '.join(self.current_tool_context['missing_params'])}. "
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
            
            import json
            decoded_json, _ = json.JSONDecoder().raw_decode(json_str_with_trailing_junk)
            return decoded_json
        except Exception as e:
            logger.error(f"[{self.category}] LLM'den geçerli JSON alınamadı: {e}")
            return {"tool_name": "chat", "parameters": {"response": "Ne istediginizi anlayamadim, lutfen daha net bir sekilde ifade eder misiniz?"}}
    
    def _create_error_response(self, error_message: str) -> Generator[str, None, None]:
        """Hata yanıtı oluştur"""
        def stream_response():
            yield error_message
        return stream_response()
    
    def _summarize_result_for_user(self, result: Any) -> Generator[str, None, None]:
        """Araç sonucunu kullanıcı için özetle"""
        import json
        summary_prompt = (
            f"Bir {self.category} araci calistirildi ve sonuc olarak asagidaki JSON verisi alindi. "
            f"Bu sonucu kullanici icin kolay anlasilir, dogal bir dilde (Turkce) ozetle. "
            f"Eger bir hata varsa hatayi belirt. Teknik terimleri basitce acikla.\n\n"
            f"JSON Verisi:\n{json.dumps(result, indent=2, ensure_ascii=False)}\n"
        )
        logger.info(f"[{self.category}] Araç sonucu için LLM'den özet isteniyor.")
        return self.client.chat_stream(
            user_prompt=summary_prompt,
            use_history=False
        )