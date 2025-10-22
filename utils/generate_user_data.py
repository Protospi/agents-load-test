import random

# Create FastCPFGenerator class
class FastCPFGenerator:
    """Gerador de CPF otimizado"""
    _cache = {}
    
    @classmethod
    def generate_cpf(cls, user_id):
        """Gera CPF com cache"""
        if user_id in cls._cache:
            return cls._cache[user_id]
            
        random.seed(user_id)
        cpf = [random.randint(0, 9) for x in range(9)]
        
        for _ in range(2):
            val = sum([(len(cpf) + 1 - i) * v for i, v in enumerate(cpf)]) % 11
            cpf.append(11 - val if val > 1 else 0)
        
        formatted = '%s%s%s.%s%s%s.%s%s%s-%s%s' % tuple(cpf)
        cls._cache[user_id] = formatted
        return formatted
    
    @staticmethod
    def cpf_only_numbers(cpf_formatted):
        return ''.join(filter(str.isdigit, cpf_formatted))

# Create OptimizedUserData class
class OptimizedUserData:
    """Geração de dados otimizada com cache"""
    _cache = {}
    
    @classmethod
    def generate_data(cls, user_id):
        if user_id in cls._cache:
            return cls._cache[user_id]
            
        import string
        random.seed(user_id)
        
        # Telefone (with country code 55)
        telefone_numero = ''.join([str(random.randint(0, 9)) for _ in range(8)])
        telefone = f"5545{telefone_numero}"
        
        # Email
        nome_base = ''.join(random.choices(string.ascii_lowercase, k=8))
        email = f"{nome_base}@smarttalks.com.br"
        
        # CPF
        cpf_formatted = FastCPFGenerator.generate_cpf(user_id)
        cpf_numbers = FastCPFGenerator.cpf_only_numbers(cpf_formatted)
        
        # Nome
        nomes = ['João', 'Maria', 'Pedro', 'Ana', 'Carlos', 'Fernanda', 'Ricardo', 'Juliana']
        nome = f"{random.choice(nomes)} {'Smart Talks'}"
        
        data = {
            'user_id': user_id,
            'telefone': telefone,
            'email': email, 
            'cpf_formatted': cpf_formatted,
            'cpf_numbers': cpf_numbers,
            'nome': nome
        }
        
        cls._cache[user_id] = data
        return data
