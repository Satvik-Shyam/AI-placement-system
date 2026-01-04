#!/usr/bin/env python3
"""
SQL Views Test Script

Tests all 3 SQL views:
1. vw_student_application_summary
2. vw_company_hiring_stats  
3. vw_skill_demand_analysis

Run: python scripts/test_views.py
"""
import sys
sys.path.insert(0, '.')

from app.db.postgres import execute_raw_sql, get_db_session
from sqlalchemy import text


def run_views_sql():
    """Execute the views.sql file to create/recreate views."""
    print("\n[0] Creating/Recreating SQL Views...")
    
    # Read the views.sql file
    with open('scripts/views.sql', 'r') as f:
        views_sql = f.read()
    
    # Split by semicolon and execute each statement
    with get_db_session() as db:
        # Execute DROP and CREATE VIEW statements
        statements = [
            # View 1
            "DROP VIEW IF EXISTS vw_student_application_summary CASCADE",
            # View 2  
            "DROP VIEW IF EXISTS vw_company_hiring_stats CASCADE",
            # View 3
            "DROP VIEW IF EXISTS vw_skill_demand_analysis CASCADE",
        ]
        
        for stmt in statements:
            db.execute(text(stmt))
        
        # Now create views - extract CREATE VIEW statements
        # We'll execute the whole file
        db.execute(text(views_sql))
    
    print("    ✅ Views created successfully")


def test_view_1_student_summary():
    """Test vw_student_application_summary view."""
    print("\n" + "=" * 60)
    print("[1] VIEW: vw_student_application_summary")
    print("=" * 60)
    
    print("\n📋 Purpose: Comprehensive student profile with application statistics")
    print("📋 Joins: users, students, student_skills, skills, applications, ai_recommendations")
    print("📋 Aggregations: COUNT, AVG, STRING_AGG")
    
    # Query the view
    results = execute_raw_sql("""
        SELECT 
            student_id,
            full_name,
            email,
            university,
            cgpa,
            total_skills,
            skills_list,
            total_applications,
            shortlisted_count,
            offers_received,
            active_recommendations,
            avg_match_score,
            profile_status
        FROM vw_student_application_summary
        ORDER BY student_id
        LIMIT 5
    """)
    
    if results:
        print(f"\n✅ View returned {len(results)} row(s):\n")
        for row in results:
            print(f"   Student: {row['full_name']} (ID: {row['student_id']})")
            print(f"   Email: {row['email']}")
            print(f"   University: {row['university']}, CGPA: {row['cgpa']}")
            print(f"   Skills ({row['total_skills']}): {row['skills_list'][:50] if row['skills_list'] else 'None'}...")
            print(f"   Applications: {row['total_applications']} total, {row['shortlisted_count']} shortlisted, {row['offers_received']} offers")
            print(f"   AI Recommendations: {row['active_recommendations']} active, Avg Score: {row['avg_match_score']}")
            print(f"   Profile Status: {row['profile_status']}")
            print()
    else:
        print("\n⚠️  No students found (this is okay if no test data exists)")
    
    # Show the view structure
    print("📊 View Columns:")
    columns = execute_raw_sql("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'vw_student_application_summary'
        ORDER BY ordinal_position
    """)
    for col in columns:
        print(f"   - {col['column_name']}: {col['data_type']}")
    
    return len(results) if results else 0


def test_view_2_company_stats():
    """Test vw_company_hiring_stats view."""
    print("\n" + "=" * 60)
    print("[2] VIEW: vw_company_hiring_stats")
    print("=" * 60)
    
    print("\n📋 Purpose: Company hiring analytics and job performance")
    print("📋 Joins: users, companies, jobs, applications, job_required_skills, skills")
    print("📋 Aggregations: COUNT, AVG, SUM, MAX")
    
    # Query the view
    results = execute_raw_sql("""
        SELECT 
            company_id,
            company_name,
            industry,
            company_size,
            is_verified,
            total_jobs_posted,
            active_jobs,
            total_applications_received,
            candidates_shortlisted,
            offers_extended,
            hires_completed,
            avg_applications_per_job,
            offer_rate_percentage,
            total_open_positions,
            most_required_skill
        FROM vw_company_hiring_stats
        ORDER BY company_id
        LIMIT 5
    """)
    
    if results:
        print(f"\n✅ View returned {len(results)} row(s):\n")
        for row in results:
            print(f"   Company: {row['company_name']} (ID: {row['company_id']})")
            print(f"   Industry: {row['industry']}, Size: {row['company_size']}, Verified: {row['is_verified']}")
            print(f"   Jobs: {row['total_jobs_posted']} total, {row['active_jobs']} active, {row['total_open_positions']} positions")
            print(f"   Applications: {row['total_applications_received']} received, {row['avg_applications_per_job']} avg/job")
            print(f"   Pipeline: {row['candidates_shortlisted']} shortlisted → {row['offers_extended']} offers → {row['hires_completed']} hires")
            print(f"   Offer Rate: {row['offer_rate_percentage']}%")
            print(f"   Most Required Skill: {row['most_required_skill']}")
            print()
    else:
        print("\n⚠️  No companies found (this is okay if no test data exists)")
    
    # Show column count
    columns = execute_raw_sql("""
        SELECT COUNT(*) as col_count
        FROM information_schema.columns 
        WHERE table_name = 'vw_company_hiring_stats'
    """)
    print(f"📊 Total columns in view: {columns[0]['col_count']}")
    
    return len(results) if results else 0


def test_view_3_skill_demand():
    """Test vw_skill_demand_analysis view."""
    print("\n" + "=" * 60)
    print("[3] VIEW: vw_skill_demand_analysis")
    print("=" * 60)
    
    print("\n📋 Purpose: Analyze skill demand vs supply in placement market")
    print("📋 Joins: skills, student_skills, job_required_skills, jobs")
    print("📋 Aggregations: COUNT with GROUP BY, CASE expressions")
    
    # Query the view - show skills with demand
    results = execute_raw_sql("""
        SELECT 
            skill_id,
            skill_name,
            skill_category,
            students_with_skill,
            jobs_requiring_mandatory,
            jobs_preferring_skill,
            total_job_demand,
            supply_demand_ratio,
            market_status,
            avg_proficiency_score,
            successful_placements,
            jobs_last_30_days
        FROM vw_skill_demand_analysis
        WHERE students_with_skill > 0 OR total_job_demand > 0
        ORDER BY total_job_demand DESC NULLS LAST, students_with_skill DESC
        LIMIT 10
    """)
    
    if results:
        print(f"\n✅ View returned {len(results)} row(s) with demand/supply:\n")
        print(f"   {'Skill':<20} {'Category':<15} {'Supply':<8} {'Demand':<8} {'Ratio':<8} {'Status':<25}")
        print("   " + "-" * 90)
        for row in results:
            ratio = f"{row['supply_demand_ratio']:.2f}" if row['supply_demand_ratio'] else "N/A"
            print(f"   {row['skill_name']:<20} {row['skill_category'] or 'N/A':<15} {row['students_with_skill']:<8} {row['total_job_demand']:<8} {ratio:<8} {row['market_status']:<25}")
    else:
        print("\n⚠️  No skills with demand/supply found")
    
    # Show market status distribution
    print("\n📊 Market Status Distribution:")
    status_dist = execute_raw_sql("""
        SELECT market_status, COUNT(*) as count
        FROM vw_skill_demand_analysis
        GROUP BY market_status
        ORDER BY count DESC
    """)
    for row in status_dist:
        print(f"   - {row['market_status']}: {row['count']} skills")
    
    return len(results) if results else 0


def test_view_queries():
    """Test some practical queries using the views."""
    print("\n" + "=" * 60)
    print("[4] PRACTICAL VIEW QUERIES")
    print("=" * 60)
    
    # Query 1: Top students by recommendations
    print("\n📊 Query 1: Students with best AI match scores")
    results = execute_raw_sql("""
        SELECT full_name, university, total_skills, avg_match_score, profile_status
        FROM vw_student_application_summary
        WHERE avg_match_score IS NOT NULL
        ORDER BY avg_match_score DESC
        LIMIT 3
    """)
    if results:
        for row in results:
            print(f"   {row['full_name']} ({row['university']}): {row['avg_match_score']} avg score, {row['total_skills']} skills")
    else:
        print("   No data available")
    
    # Query 2: Most active hiring companies
    print("\n📊 Query 2: Companies with most applications received")
    results = execute_raw_sql("""
        SELECT company_name, industry, total_applications_received, offer_rate_percentage
        FROM vw_company_hiring_stats
        WHERE total_applications_received > 0
        ORDER BY total_applications_received DESC
        LIMIT 3
    """)
    if results:
        for row in results:
            print(f"   {row['company_name']} ({row['industry']}): {row['total_applications_received']} apps, {row['offer_rate_percentage']}% offer rate")
    else:
        print("   No data available")
    
    # Query 3: Skills in high demand with shortage
    print("\n📊 Query 3: Skills with high demand but low supply (skill gaps)")
    results = execute_raw_sql("""
        SELECT skill_name, skill_category, students_with_skill, total_job_demand, market_status
        FROM vw_skill_demand_analysis
        WHERE market_status = 'High Demand - Skill Shortage'
        ORDER BY total_job_demand DESC
        LIMIT 5
    """)
    if results:
        for row in results:
            print(f"   {row['skill_name']}: {row['students_with_skill']} students, {row['total_job_demand']} jobs need it")
    else:
        print("   No skill gaps detected (or insufficient data)")
    
    print("\n✅ Practical queries completed")


def verify_views_exist():
    """Verify all 3 views exist in database."""
    print("\n[5] Verifying views exist in database...")
    
    results = execute_raw_sql("""
        SELECT table_name as view_name
        FROM information_schema.views
        WHERE table_schema = 'public'
        AND table_name LIKE 'vw_%'
        ORDER BY table_name
    """)
    
    expected_views = [
        'vw_company_hiring_stats',
        'vw_skill_demand_analysis',
        'vw_student_application_summary'
    ]
    
    found_views = [r['view_name'] for r in results]
    
    print(f"\n   Found {len(found_views)} views:")
    for view in found_views:
        status = "✅" if view in expected_views else "⚠️"
        print(f"   {status} {view}")
    
    # Check if all expected views exist
    missing = set(expected_views) - set(found_views)
    if missing:
        print(f"\n   ❌ Missing views: {missing}")
        return False
    
    print(f"\n   ✅ All 3 required views exist!")
    return True


def main():
    print("=" * 60)
    print("SQL VIEWS TEST")
    print("=" * 60)
    
    try:
        # First, verify views exist (don't recreate, use existing)
        if not verify_views_exist():
            print("\n⚠️  Some views missing. Run this in psql first:")
            print("   \\i scripts/views.sql")
            return
        
        # Test each view
        count1 = test_view_1_student_summary()
        count2 = test_view_2_company_stats()
        count3 = test_view_3_skill_demand()
        
        # Test practical queries
        test_view_queries()
        
        print("\n" + "=" * 60)
        print("✅ ALL VIEW TESTS COMPLETED!")
        print("=" * 60)
        
        print("\n📊 Summary:")
        print(f"   View 1 (Student Summary): {count1} rows")
        print(f"   View 2 (Company Stats): {count2} rows")
        print(f"   View 3 (Skill Demand): {count3} rows")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()