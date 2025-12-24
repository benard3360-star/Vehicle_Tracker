import openai
import json
from django.conf import settings
from .models import VehicleMovement, Vehicle

class AIAssistantService:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
    
    def get_vehicle_context(self, user_org):
        """Get vehicle data context for AI"""
        movements = VehicleMovement.objects.filter(
            organization=user_org
        ).select_related('vehicle')[:50]
        
        context = []
        for movement in movements:
            context.append({
                'plate': movement.plate_number,
                'entry_time': str(movement.entry_time),
                'exit_time': str(movement.exit_time) if movement.exit_time else 'Still parked',
                'amount': float(movement.amount_paid),
                'location': movement.organization
            })
        
        return context
    
    def chat_response(self, user_message, user_org):
        """Generate AI response with vehicle context"""
        vehicle_data = self.get_vehicle_context(user_org)
        
        system_prompt = f"""
        You are a vehicle intelligence assistant. Help users with parking and vehicle movement queries.
        
        Available vehicle data: {json.dumps(vehicle_data[:10])}
        
        Answer questions about:
        - Vehicle locations and parking status
        - Parking costs and payments
        - Movement patterns and history
        - Parking duration analysis
        
        Keep responses concise and helpful.
        """
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",  # Cost-effective option
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Sorry, I'm having trouble processing your request. Please try again."