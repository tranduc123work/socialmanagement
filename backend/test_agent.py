"""
Test script cho AI Agent
Chạy: python test_agent.py
"""
import os
import django
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.auth.models import User
from apps.agent.services import AgentToolExecutor, AgentConversationService
from apps.agent.llm_agent import get_agent
from datetime import datetime, timedelta
from django.utils import timezone


def print_section(title):
    """Print section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def test_get_scheduled_posts():
    """Test 1: Get scheduled posts với date filtering"""
    print_section("TEST 1: Get Scheduled Posts với Date Filtering")

    user = User.objects.first()
    if not user:
        print("❌ Không tìm thấy user. Tạo user trước.")
        return False

    print(f"User: {user.username}")

    # Test 1.1: Get all posts
    print("\n1.1 - Get all posts (no filter):")
    result = AgentToolExecutor.get_scheduled_posts(user)
    print(f"   Total: {result['total']}")
    print(f"   Posts returned: {len(result['posts'])}")

    # Test 1.2: Get posts in next 7 days
    print("\n1.2 - Get posts in next 7 days (days_ahead=7):")
    result = AgentToolExecutor.get_scheduled_posts(user, days_ahead=7)
    print(f"   Total: {result['total']}")
    print(f"   Date range: {result['date_range']}")
    if result['posts']:
        print("   Posts:")
        for post in result['posts']:
            print(f"     - {post['schedule_date']}: {post['title']}")

    # Test 1.3: Get draft posts
    print("\n1.3 - Get draft posts only:")
    result = AgentToolExecutor.get_scheduled_posts(user, status='draft')
    print(f"   Total drafts: {result['total']}")

    # Test 1.4: Get posts in specific date range
    print("\n1.4 - Get posts in specific date range:")
    today = timezone.now().date()
    end_date = today + timedelta(days=3)
    result = AgentToolExecutor.get_scheduled_posts(
        user,
        start_date=str(today),
        end_date=str(end_date)
    )
    print(f"   Total: {result['total']}")
    print(f"   Date range: {result['date_range']}")

    print("\n✅ Test 1 completed")
    return True


def test_get_system_stats():
    """Test 2: Get system stats"""
    print_section("TEST 2: Get System Stats")

    user = User.objects.first()
    if not user:
        print("❌ Không tìm thấy user")
        return False

    result = AgentToolExecutor.get_system_stats(user)

    print(f"Scheduled Posts:")
    print(f"  - Total: {result['scheduled_posts']['total']}")
    print(f"  - Draft: {result['scheduled_posts']['draft']}")
    print(f"  - Published: {result['scheduled_posts']['published']}")
    print(f"\nSchedules: {result['schedules']}")
    print(f"Agent Posts: {result['agent_posts']}")
    print(f"Media Files: {result['media']}")
    print(f"\nSummary: {result['summary']}")

    print("\n✅ Test 2 completed")
    return True


def test_generate_content():
    """Test 3: Generate post content"""
    print_section("TEST 3: Generate Post Content")

    user = User.objects.first()
    if not user:
        print("❌ Không tìm thấy user")
        return False

    print("Generating content...")
    result = AgentToolExecutor.generate_post_content(
        user=user,
        business_type="Mái lợp nhựa",
        topic="Tiết kiệm điện mùa hè",
        goal="awareness",
        tone="professional"
    )

    if result.get('success'):
        print("✅ Content generated successfully!")
        print(f"\nContent preview (first 200 chars):")
        print(result['content'][:200] + "...")
        print(f"\nHashtags: {result['hashtags']}")
    else:
        print(f"❌ Failed to generate content: {result.get('error')}")
        return False

    print("\n✅ Test 3 completed")
    return True


def test_create_agent_post():
    """Test 4: Create agent post (without image for speed)"""
    print_section("TEST 4: Create Agent Post")

    user = User.objects.first()
    if not user:
        print("❌ Không tìm thấy user")
        return False

    print("Creating agent post...")
    result = AgentToolExecutor.create_agent_post(
        user=user,
        content="Đây là bài test từ agent.\n\nMục đích: Kiểm tra tính năng tạo bài tự động.",
        hashtags=["#test", "#agent", "#automation"],
        # Skip image generation for faster testing
        image_description=None,
        strategy={'test': True}
    )

    if result.get('success'):
        print("✅ Post created successfully!")
        print(f"Post ID: {result['post_id']}")
        print(f"Content: {result['content'][:100]}...")
        print(f"Message: {result['message']}")
    else:
        print(f"❌ Failed to create post: {result.get('error')}")
        return False

    print("\n✅ Test 4 completed")
    return True


def test_agent_conversation():
    """Test 5: Full agent conversation"""
    print_section("TEST 5: Agent Conversation")

    user = User.objects.first()
    if not user:
        print("❌ Không tìm thấy user")
        return False

    test_messages = [
        "Có bao nhiêu bài đăng đã lên lịch?",
        "Số bài đăng trong 7 ngày tới",
        "Có bao nhiêu bài draft?",
    ]

    for i, message in enumerate(test_messages, 1):
        print(f"\n{i}. User: {message}")

        try:
            response = AgentConversationService.send_message(user, message)

            print(f"   Agent: {response['agent_response'][:200]}...")

            if response['function_calls']:
                print(f"   Function calls:")
                for fc in response['function_calls']:
                    print(f"     - {fc['name']}({fc.get('args', {})})")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    print("\n✅ Test 5 completed")
    return True


def test_tool_definitions():
    """Test 6: Verify tool definitions"""
    print_section("TEST 6: Verify Tool Definitions")

    agent = get_agent()
    tools = agent._define_tools()

    print(f"Total tools defined: {len(tools)}")
    print("\nTools:")
    for i, tool in enumerate(tools, 1):
        print(f"\n{i}. {tool['name']}")
        print(f"   Description: {tool['description'][:80]}...")
        params = tool['parameters']['properties']
        print(f"   Parameters: {', '.join(params.keys())}")

    # Verify get_scheduled_posts has date params
    get_posts_tool = next((t for t in tools if t['name'] == 'get_scheduled_posts'), None)
    if get_posts_tool:
        params = get_posts_tool['parameters']['properties']
        required_params = ['days_ahead', 'start_date', 'end_date']
        has_all = all(p in params for p in required_params)
        if has_all:
            print("\n✅ get_scheduled_posts has all date parameters")
        else:
            print(f"\n❌ Missing date parameters in get_scheduled_posts")
            return False

    print("\n✅ Test 6 completed")
    return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "🤖 AI AGENT TEST SUITE".center(60))
    print("="*60)

    tests = [
        ("Tool Definitions", test_tool_definitions),
        ("Get Scheduled Posts", test_get_scheduled_posts),
        ("Get System Stats", test_get_system_stats),
        ("Generate Content", test_generate_content),
        ("Create Agent Post", test_create_agent_post),
        ("Agent Conversation", test_agent_conversation),
    ]

    results = []

    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ Test '{name}' failed with exception:")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # Summary
    print_section("TEST RESULTS SUMMARY")

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")

    total = len(results)
    passed = sum(1 for _, success in results if success)
    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")


if __name__ == '__main__':
    run_all_tests()
