#!/usr/bin/env python3
"""
Script to create test data for dashboard verification
"""
import os
import sys
from datetime import datetime, timedelta
from app import app, db
from models import ChatSessionForDashboard, MessengerSession, Lead

def create_test_data():
    """Create comprehensive test data for dashboard verification"""
    
    with app.app_context():
        try:
            # Test session 1: Complete lead generation conversation
            session_id_1 = "test_session_demo_001"
            base_time_1 = datetime.utcnow() - timedelta(hours=2)
            
            # Create messenger session 1
            messenger_session_1 = MessengerSession(
                session_id=session_id_1,
                conversation_start=base_time_1,
                last_message_time=base_time_1 + timedelta(minutes=15),
                message_count=8,
                status='active',
                completion_status='complete',
                qa_status='unchecked',
                ai_engaged=True,
                session_source='web_chat'
            )
            db.session.add(messenger_session_1)
            
            # Create lead 1
            lead_1 = Lead(
                session_id=session_id_1,
                full_name="Emily Rodriguez",
                company_name="TechStart Solutions",
                email="emily@techstart.com",
                phone_number="+1-555-0123",
                ai_interest_reason="Looking to automate customer support with AI chatbots",
                ai_implementation_known="Want to integrate with existing CRM system",
                ai_implementation_timeline="3-6 months",
                ai_budget_allocated="Yes, allocated $50K for AI initiatives",
                business_goals_6_12m="Scale customer support to handle 500% growth",
                business_challenges="Current support team overwhelmed, response times too slow"
            )
            db.session.add(lead_1)
            
            # Create chat messages 1
            messages_1 = [
                ChatSessionForDashboard(
                    session_id=session_id_1,
                    messageStr="Hello! I'm interested in learning about AI solutions for my business.",
                    userAi='user',
                    dateTime=base_time_1
                ),
                ChatSessionForDashboard(
                    session_id=session_id_1,
                    messageStr="Great to meet you! I'd love to help you explore AI solutions. What's your name and what kind of business are you running?",
                    userAi='ai',
                    dateTime=base_time_1 + timedelta(minutes=1)
                ),
                ChatSessionForDashboard(
                    session_id=session_id_1,
                    messageStr="I'm Emily Rodriguez, CEO of TechStart Solutions. We're a SaaS company experiencing rapid growth.",
                    userAi='user',
                    dateTime=base_time_1 + timedelta(minutes=2)
                ),
                ChatSessionForDashboard(
                    session_id=session_id_1,
                    messageStr="Congratulations on your growth, Emily! What specific challenges are you facing that AI might help solve?",
                    userAi='ai',
                    dateTime=base_time_1 + timedelta(minutes=3)
                ),
                ChatSessionForDashboard(
                    session_id=session_id_1,
                    messageStr="Our customer support is overwhelmed. We need to scale but can't hire fast enough. I'm thinking AI chatbots could help.",
                    userAi='user',
                    dateTime=base_time_1 + timedelta(minutes=5)
                ),
                ChatSessionForDashboard(
                    session_id=session_id_1,
                    messageStr="AI-powered customer support is a perfect fit for scaling SaaS companies. Do you have budget allocated for AI initiatives?",
                    userAi='ai',
                    dateTime=base_time_1 + timedelta(minutes=7)
                ),
                ChatSessionForDashboard(
                    session_id=session_id_1,
                    messageStr="Yes, we've allocated $50K for AI this year. Timeline is 3-6 months. Can you help us get started?",
                    userAi='user',
                    dateTime=base_time_1 + timedelta(minutes=10)
                ),
                ChatSessionForDashboard(
                    session_id=session_id_1,
                    messageStr="Absolutely! I'll have our team reach out within 24 hours with a customized proposal for TechStart Solutions. Thank you for your time today, Emily!",
                    userAi='ai',
                    dateTime=base_time_1 + timedelta(minutes=15)
                )
            ]
            
            for msg in messages_1:
                db.session.add(msg)
            
            # Test session 2: In-progress conversation
            session_id_2 = "test_session_demo_002"
            base_time_2 = datetime.utcnow() - timedelta(hours=1)
            
            # Create messenger session 2
            messenger_session_2 = MessengerSession(
                session_id=session_id_2,
                conversation_start=base_time_2,
                last_message_time=base_time_2 + timedelta(minutes=8),
                message_count=6,
                status='active',
                completion_status='in_progress',
                qa_status='unchecked',
                ai_engaged=True,
                session_source='web_chat'
            )
            db.session.add(messenger_session_2)
            
            # Create lead 2
            lead_2 = Lead(
                session_id=session_id_2,
                full_name="Marcus Chen",
                company_name="DataFlow Analytics",
                email="marcus@dataflow.io",
                phone_number="+1-555-0789",
                ai_interest_reason="Need AI for data processing and analytics automation",
                ai_implementation_known="Exploring machine learning models for predictive analytics",
                ai_implementation_timeline="6-12 months",
                ai_budget_allocated="Evaluating budget options",
                business_goals_6_12m="Launch AI-powered analytics platform",
                business_challenges="Manual data processing is bottleneck for growth"
            )
            db.session.add(lead_2)
            
            # Create chat messages 2
            messages_2 = [
                ChatSessionForDashboard(
                    session_id=session_id_2,
                    messageStr="Hi there! I'm exploring AI solutions for data analytics. Can you help?",
                    userAi='user',
                    dateTime=base_time_2
                ),
                ChatSessionForDashboard(
                    session_id=session_id_2,
                    messageStr="Absolutely! AI can transform data analytics. What's your name and what type of data challenges are you facing?",
                    userAi='ai',
                    dateTime=base_time_2 + timedelta(minutes=1)
                ),
                ChatSessionForDashboard(
                    session_id=session_id_2,
                    messageStr="I'm Marcus Chen from DataFlow Analytics. We're processing tons of data manually and need automation.",
                    userAi='user',
                    dateTime=base_time_2 + timedelta(minutes=3)
                ),
                ChatSessionForDashboard(
                    session_id=session_id_2,
                    messageStr="Perfect, Marcus! Manual data processing is exactly where AI shines. What's your timeline for implementing a solution?",
                    userAi='ai',
                    dateTime=base_time_2 + timedelta(minutes=5)
                ),
                ChatSessionForDashboard(
                    session_id=session_id_2,
                    messageStr="We're thinking 6-12 months. Still evaluating our budget though. What kind of ROI can we expect?",
                    userAi='user',
                    dateTime=base_time_2 + timedelta(minutes=7)
                ),
                ChatSessionForDashboard(
                    session_id=session_id_2,
                    messageStr="Great question! Most clients see 3-5x ROI within the first year through automation savings. Would you like me to schedule a detailed ROI analysis call?",
                    userAi='ai',
                    dateTime=base_time_2 + timedelta(minutes=8)
                )
            ]
            
            for msg in messages_2:
                db.session.add(msg)
            
            # Test session 3: Recent incomplete conversation
            session_id_3 = "test_session_demo_003"
            base_time_3 = datetime.utcnow() - timedelta(minutes=30)
            
            # Create messenger session 3
            messenger_session_3 = MessengerSession(
                session_id=session_id_3,
                conversation_start=base_time_3,
                last_message_time=base_time_3 + timedelta(minutes=5),
                message_count=4,
                status='active',
                completion_status='incomplete',
                qa_status='unchecked',
                ai_engaged=False,
                session_source='web_chat'
            )
            db.session.add(messenger_session_3)
            
            # Create lead 3
            lead_3 = Lead(
                session_id=session_id_3,
                full_name="Sarah Kim",
                company_name="RetailBoost",
                email="sarah@retailboost.com",
                phone_number="+1-555-0456",
                ai_interest_reason="Just browsing, not sure about AI yet",
                ai_implementation_known="No specific plans",
                ai_implementation_timeline="unclear",
                ai_budget_allocated="No budget allocated yet",
                business_goals_6_12m="Improve e-commerce conversion rates",
                business_challenges="Low website conversion, cart abandonment issues"
            )
            db.session.add(lead_3)
            
            # Create chat messages 3
            messages_3 = [
                ChatSessionForDashboard(
                    session_id=session_id_3,
                    messageStr="Hello, I'm just looking around. What do you do exactly?",
                    userAi='user',
                    dateTime=base_time_3
                ),
                ChatSessionForDashboard(
                    session_id=session_id_3,
                    messageStr="Hi! We help businesses implement AI solutions to solve their biggest challenges. What kind of business are you in?",
                    userAi='ai',
                    dateTime=base_time_3 + timedelta(minutes=1)
                ),
                ChatSessionForDashboard(
                    session_id=session_id_3,
                    messageStr="I run an e-commerce store called RetailBoost. We sell fitness equipment online.",
                    userAi='user',
                    dateTime=base_time_3 + timedelta(minutes=3)
                ),
                ChatSessionForDashboard(
                    session_id=session_id_3,
                    messageStr="E-commerce is perfect for AI! We can help with personalized recommendations, inventory optimization, and customer service automation. What challenges are you facing?",
                    userAi='ai',
                    dateTime=base_time_3 + timedelta(minutes=5)
                )
            ]
            
            for msg in messages_3:
                db.session.add(msg)
            
            # Commit all test data
            db.session.commit()
            
            print("✅ Test data created successfully!")
            print("\n📊 DASHBOARD TEST DATA SUMMARY:")
            print("=" * 50)
            print("Session 1: Complete lead (Emily Rodriguez - TechStart Solutions)")
            print("  - 8 messages, completed conversation")
            print("  - High AI engagement, budget allocated")
            print("  - Timeline: 3-6 months, $50K budget")
            print()
            print("Session 2: In-progress (Marcus Chen - DataFlow Analytics)")
            print("  - 6 messages, ongoing conversation")
            print("  - AI engaged, evaluating budget")
            print("  - Timeline: 6-12 months")
            print()
            print("Session 3: Early stage (Sarah Kim - RetailBoost)")
            print("  - 4 messages, incomplete conversation")
            print("  - Low AI engagement, no budget yet")
            print("  - Timeline: unclear")
            print()
            print("🎯 All three sessions should now appear in the dashboard!")
            print("📈 Statistics should show: 3 total, 1 complete, 1 in_progress, 1 incomplete")
            
        except Exception as e:
            print(f"Error creating test data: {str(e)}")
            db.session.rollback()
            sys.exit(1)

if __name__ == "__main__":
    create_test_data()