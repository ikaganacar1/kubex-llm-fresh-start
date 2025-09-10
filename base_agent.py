from abc import ABC, abstractmethod
from typing import Dict, Any, List, Generator, Union, Optional 
import json

from llm_services.tool_calling_llm_service import ToolCallingLLMService
from llm_services.summarizer_llm_service import SummarizerLLMService

class BaseAgent(ABC):
    def __init__(self, client, category: str, description: str, manager: Optional[Any] = None):
        self.client = client
        self.category = category
        self.description = description
        self.manager = manager
        
        self.tool_llm_service = ToolCallingLLMService(self.client)
        self.summary_llm_service = SummarizerLLMService(self.client)
        
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
                if param_name != "cluster_id":
                    param_list.append(f"{param_name} ({p.get('in', 'N/A')})")

            params_str = ", ".join(param_list) if param_list else "Yok"
            tools_description_lines.append(
                f"  - Arac Adi: '{name}'\n"
                f"  - Aciklama: {details.get('summary', '')}\n"
                f"  - Gerekli Parametreler: {params_str}"
            )
        tools_prompt = "\n".join(tools_description_lines)

        context_info = ""
        if self.conversation_context:
            context_info = f"\n\n### SON SOHBET OZETI ###\n{self._get_conversation_summary()}\n"

        # --- YENİ VE DAHA NET PROMPT ---
        return (
            f"### KİMLİK VE UZMANLIK ALANI ###\n"
            f"Sen, KUBEX platformunda **{self.category}** konusunda uzmanlaşmış bir asistansın. "
            "Temel görevin, kullanıcı taleplerini analiz ederek sahip olduğun araç setini en etkili şekilde kullanmak "
            "ve istenen eylemi başarıyla tamamlamaktır.\n\n"
            f"### ARAÇ SETİ: {self.category} ###\n{tools_prompt}\n"
            f"{context_info}\n"
            "### GÖREV AKIŞI VE KURALLAR ###\n"
            "1. **Talep Analizi:** Kullanıcının talebini dikkatle analiz et. Talebin bir eylem (listeleme, oluşturma, silme vb.) içerip içermediğini belirle.\n"
            "2. **Araç Önceliği:** Eğer kullanıcının talebi, yukarıdaki ARAÇ SETİ'nde listelenen bir aracın açıklamasıyla eşleşiyorsa, o aracı kullanmak **ZORUNLUSUN**.\n"
            "3. **Sohbet İstisnası:** **SADECE** ve **SADECE** taleple eşleşen bir araç yoksa veya kullanıcı genel bir sohbet (selam, nasılsın vb.) başlatıyorsa 'chat' aracını kullan.\n\n"
            "### ÇIKTI FORMATI ###\n"
            "Analizinin sonucunu, **SADECE** aşağıda belirtilen formatta bir JSON objesi olarak döndür. "
            "Yanıtına başka hiçbir metin ekleme.\n\n"
            "1. **Bir Araç Kullanılacaksa:**\n"
            "```json\n"
            "{\n"
            '  "tool_name": "kullanilacak_aracin_adi",\n'
            '  "parameters": {}\n'
            "}\n"
            "```\n\n"
            "2. **Sohbet Yanıtı Verilecekse:**\n"
            "```json\n"
            "{\n"
            '  "tool_name": "chat",\n'
            '  "parameters": {\n'
            '    "response": "Kullanıcıya verilecek net ve yardımcı cevap."\n'
            "  }\n"
            "}\n"
            "```\n\n"
            "### KESİN KURAL ###\n"
            "Kullanıcının talebi bir eylem içeriyorsa ve bu eylem araç setindeki bir araçla yapılabiliyorsa, 'chat' kullanmak **YASAKTIR**. "
            "Doğru aracı seçip JSON çıktısını üret."
        )
    

    def reset_context(self):
        """Bağlamı sıfırla"""
        self.waiting_for_parameters = False
        self.current_tool_context = None
        # YENI: Tam reset yapmak yerine conversation_context'i koru
        # self.conversation_context = []  # Bunu kaldırdık
        self.last_user_request = None
    
    def add_to_conversation_context(self, user_message: str, assistant_response: str):
        self.conversation_context.append({
            "user": user_message,
            "assistant": assistant_response,
            "timestamp": "recent"
        })
        
        # Memory limitini koru (son 5 etkileşim)
        if len(self.conversation_context) > 5:
            self.conversation_context = self.conversation_context[-5:]
    
    def _get_conversation_summary(self) -> str:
        if not self.conversation_context:
            return "Henuz bir sohbet gecmisi yok."
            
        summary_parts = []
        for i, interaction in enumerate(self.conversation_context[-3:], 1):  # Son 3 etkileşim
            user_msg = interaction["user"][:100] + "..." if len(interaction["user"]) > 100 else interaction["user"]
            assistant_msg = interaction["assistant"][:100] + "..." if len(interaction["assistant"]) > 100 else interaction["assistant"]
            summary_parts.append(f"{i}. Kullanici: {user_msg}\n   Asistan: {assistant_msg}")
        
        return "\n".join(summary_parts)
    
    def process_request(self, prompt: str) -> Union[Dict[str, Any], Generator[str, None, None]]:        
        self.last_user_request = prompt

        context_reminder = None
        if self.waiting_for_parameters and self.current_tool_context:
            context_reminder = (
                f"BAGLAM: Daha once '{self.current_tool_context['tool_name']}' aracini sectim. "
                f"Eksik parametreler: {', '.join(self.current_tool_context['missing_params'])}. "
                f"ORIJINAL ISTEK: {self.current_tool_context.get('original_request', 'bilinmiyor')}"
            )
        
        llm_decision = self.tool_llm_service.select_tool(
            user_prompt=prompt,
            agent_category=self.category,
            tools=self.get_tools(),
            conversation_summary=self._get_conversation_summary(),
            context_reminder=context_reminder
        )
        
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
   
    def _create_error_response(self, error_message: str) -> Generator[str, None, None]:
        """Hata yanıtı oluştur"""
        # YENI: Error'u da context'e ekle
        if self.last_user_request:
            self.add_to_conversation_context(self.last_user_request, error_message)
            
        def stream_response():
            yield error_message
        return stream_response()
    
    def _summarize_result_for_user(self, result: Any, original_request: str = None) -> Generator[str, None, None]:
        if not original_request:
            original_request = self.last_user_request or "Bilinmeyen istek"

        response_generator = self.summary_llm_service.summarize_stream(
            tool_result=result,
            original_request=original_request,
            agent_category=self.category
        )
        
        full_response = "".join(list(response_generator))
            
        if original_request:
            self.add_to_conversation_context(original_request, full_response)
        
        def stream_wrapper():
            yield full_response
        return stream_wrapper()