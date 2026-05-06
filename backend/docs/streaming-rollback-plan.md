# Streaming Feature Rollback Plan

## Overview

This document provides a comprehensive rollback plan for the ChatBI streaming feature. It covers rollback triggers, procedures, verification steps, and recovery strategies.

## Rollback Decision Matrix

### When to Rollback

Initiate rollback immediately if:

| Condition | Threshold | Severity | Action |
|-----------|-----------|----------|--------|
| Success rate drops | < 80% | Critical | Immediate rollback |
| Error rate spikes | > 20% | Critical | Immediate rollback |
| TTFC increases | > 10 seconds (avg) | Critical | Immediate rollback |
| WebSocket disconnections | > 30% | Critical | Immediate rollback |
| Security issue | Any critical issue | Critical | Immediate rollback |
| Data corruption | Any occurrence | Critical | Immediate rollback |
| System crash | Multiple crashes | Critical | Immediate rollback |

### When to Monitor (No Rollback Yet)

Monitor closely if:

| Condition | Threshold | Severity | Action |
|-----------|-----------|----------|--------|
| Success rate drops | 80-90% | Warning | Monitor for 15 minutes |
| Error rate increases | 10-20% | Warning | Investigate immediately |
| TTFC increases | 5-10 seconds | Warning | Monitor and optimize |
| User complaints | > 5 in 1 hour | Warning | Investigate issues |

## Rollback Procedures

### Quick Rollback (< 5 minutes)

This is the fastest rollback method, disabling streaming via configuration.

#### Step 1: Disable Streaming via Configuration

**Backend**:
```bash
# SSH to backend server
ssh user@backend-server

# Update environment variable
cd /opt/chatbi/backend
echo "ENABLE_STREAMING=false" >> .env

# Restart backend service
sudo systemctl restart chatbi-backend

# Verify service is running
sudo systemctl status chatbi-backend
```

**Frontend**:
```bash
# SSH to frontend server (or update via CI/CD)
ssh user@frontend-server

# Update environment variable
cd /opt/chatbi/frontend
echo "VITE_ENABLE_STREAMING=false" > .env.production

# Rebuild frontend
npm run build

# Deploy updated build
sudo cp -r dist/* /var/www/chatbi/

# Clear CDN cache
./scripts/clear_cdn_cache.sh
```

#### Step 2: Verify Rollback

```bash
# Test backend
curl http://localhost:8000/health

# Check logs for streaming disabled message
grep "Streaming disabled" /var/log/chatbi/backend.log

# Test frontend
curl http://localhost:5173/

# Verify in browser
# Open browser console and check for streaming disabled message
```

#### Step 3: Monitor System

```bash
# Monitor error rates
tail -f /var/log/chatbi/backend.log | grep ERROR

# Check metrics dashboard
# Open Grafana and verify metrics returning to normal
```

**Expected Time**: 3-5 minutes

---

### Full Rollback (< 15 minutes)

This rollback reverts to the previous code version.

#### Step 1: Identify Previous Version

```bash
# Check git history
git log --oneline -10

# Identify commit before streaming feature
# Example: abc1234 - "Last commit before streaming"
```

#### Step 2: Rollback Backend Code

```bash
# SSH to backend server
ssh user@backend-server

# Navigate to backend directory
cd /opt/chatbi/backend

# Stash any local changes
git stash

# Checkout previous version
git checkout abc1234

# Install dependencies (in case they changed)
pip install -r requirements.txt

# Run database migrations (if needed to rollback)
alembic downgrade -1

# Restart backend service
sudo systemctl restart chatbi-backend

# Verify service is running
sudo systemctl status chatbi-backend
```

#### Step 3: Rollback Frontend Code

```bash
# SSH to frontend server
ssh user@frontend-server

# Navigate to frontend directory
cd /opt/chatbi/frontend

# Stash any local changes
git stash

# Checkout previous version
git checkout abc1234

# Install dependencies (in case they changed)
npm install

# Build frontend
npm run build

# Deploy updated build
sudo cp -r dist/* /var/www/chatbi/

# Clear CDN cache
./scripts/clear_cdn_cache.sh
```

#### Step 4: Verify Rollback

```bash
# Test backend
curl http://localhost:8000/health

# Test frontend
curl http://localhost:5173/

# Run smoke tests
./scripts/run_smoke_tests.sh

# Check logs for errors
tail -100 /var/log/chatbi/backend.log | grep ERROR
```

#### Step 5: Monitor System

```bash
# Monitor metrics for 30 minutes
# Check Grafana dashboard
# Verify error rates return to normal
# Verify success rates return to normal
```

**Expected Time**: 10-15 minutes

---

### Database Rollback (if needed)

If database migrations were part of the streaming deployment:

#### Step 1: Backup Current Database

```bash
# Create backup before rollback
./scripts/backup_database.sh

# Verify backup created
ls -lh /backups/database/
```

#### Step 2: Rollback Database Migrations

```bash
# SSH to backend server
ssh user@backend-server

# Navigate to backend directory
cd /opt/chatbi/backend

# Check current migration version
alembic current

# Rollback to previous version
alembic downgrade -1

# Verify rollback
alembic current
```

#### Step 3: Verify Database State

```bash
# Connect to database
psql -U chatbi_user -d chatbi_db

# Verify tables and schema
\dt
\d+ table_name

# Run test queries
SELECT COUNT(*) FROM sessions;
```

**Expected Time**: 5-10 minutes

---

## Rollback Verification Checklist

After rollback, verify:

### Backend Verification

- [ ] Backend service is running
  ```bash
  sudo systemctl status chatbi-backend
  ```

- [ ] Health endpoint responds
  ```bash
  curl http://localhost:8000/health
  ```

- [ ] No errors in logs
  ```bash
  tail -100 /var/log/chatbi/backend.log | grep ERROR
  ```

- [ ] Database connectivity works
  ```bash
  # Test database connection
  python -c "from src.database import engine; engine.connect()"
  ```

- [ ] API endpoints respond correctly
  ```bash
  # Test query endpoint
  curl -X POST http://localhost:8000/api/query \
    -H "Content-Type: application/json" \
    -d '{"question": "test query"}'
  ```

### Frontend Verification

- [ ] Frontend loads correctly
  ```bash
  curl http://localhost:5173/
  ```

- [ ] No JavaScript errors in console
  - Open browser console (F12)
  - Check for errors
  - Verify no streaming-related errors

- [ ] Query submission works
  - Submit test query
  - Verify results appear
  - Verify no streaming behavior

- [ ] UI is responsive
  - Test navigation
  - Test interactions
  - Verify no lag or freezing

### System Verification

- [ ] Metrics return to baseline
  - Check Grafana dashboard
  - Verify error rates normal
  - Verify success rates normal

- [ ] No new errors reported
  - Check error tracking (Sentry)
  - Review recent errors
  - Verify no streaming-related errors

- [ ] User feedback positive
  - Check support tickets
  - Monitor user complaints
  - Verify issues resolved

## Post-Rollback Actions

### Immediate Actions (Within 1 Hour)

1. [ ] **Notify Team**
   - Send rollback notification
   - Explain reason for rollback
   - Provide status update

2. [ ] **Update Status Page**
   - Mark incident as resolved
   - Explain what happened
   - Provide timeline

3. [ ] **Document Incident**
   - Record rollback reason
   - Document steps taken
   - Note lessons learned

4. [ ] **Monitor System**
   - Watch metrics closely for 1 hour
   - Check logs frequently
   - Respond to any issues

### Short-Term Actions (Within 24 Hours)

1. [ ] **Root Cause Analysis**
   - Investigate what went wrong
   - Identify contributing factors
   - Document findings

2. [ ] **Fix Planning**
   - Determine fix approach
   - Estimate fix timeline
   - Plan testing strategy

3. [ ] **Communication**
   - Update stakeholders
   - Communicate fix plan
   - Set expectations

4. [ ] **Metrics Review**
   - Analyze metrics from deployment
   - Identify warning signs
   - Improve monitoring

### Long-Term Actions (Within 1 Week)

1. [ ] **Implement Fix**
   - Develop fix for root cause
   - Test thoroughly
   - Prepare for re-deployment

2. [ ] **Improve Testing**
   - Add tests for failure scenario
   - Improve test coverage
   - Enhance integration tests

3. [ ] **Update Procedures**
   - Update deployment checklist
   - Improve rollback plan
   - Enhance monitoring

4. [ ] **Post-Mortem**
   - Conduct team post-mortem
   - Document lessons learned
   - Share with organization

## Rollback Scenarios and Solutions

### Scenario 1: High Error Rate

**Symptoms**:
- Error rate > 20%
- Many streaming interruptions
- User complaints

**Rollback Steps**:
1. Execute Quick Rollback (disable streaming)
2. Verify error rate drops
3. Investigate root cause
4. Fix and re-deploy

**Root Cause Investigation**:
- Check AI model errors
- Review network issues
- Analyze error logs
- Identify patterns

---

### Scenario 2: Performance Degradation

**Symptoms**:
- TTFC > 10 seconds
- Slow chunk delivery
- System lag

**Rollback Steps**:
1. Execute Quick Rollback (disable streaming)
2. Verify performance improves
3. Investigate bottlenecks
4. Optimize and re-deploy

**Root Cause Investigation**:
- Check AI model performance
- Review network latency
- Analyze resource usage
- Identify bottlenecks

---

### Scenario 3: WebSocket Connection Issues

**Symptoms**:
- High disconnection rate (> 30%)
- Connection failures
- Timeout errors

**Rollback Steps**:
1. Execute Quick Rollback (disable streaming)
2. Verify connections stable
3. Investigate WebSocket issues
4. Fix and re-deploy

**Root Cause Investigation**:
- Check WebSocket server logs
- Review load balancer config
- Analyze network issues
- Test connection stability

---

### Scenario 4: Data Corruption

**Symptoms**:
- Incorrect data displayed
- Database inconsistencies
- Data loss

**Rollback Steps**:
1. Execute Full Rollback (code + database)
2. Restore database from backup
3. Verify data integrity
4. Investigate corruption cause

**Root Cause Investigation**:
- Check database logs
- Review migration scripts
- Analyze data flow
- Identify corruption point

---

### Scenario 5: Security Issue

**Symptoms**:
- Security vulnerability discovered
- Unauthorized access
- Data breach

**Rollback Steps**:
1. Execute Immediate Rollback
2. Disable affected endpoints
3. Investigate security issue
4. Implement fix and re-deploy

**Root Cause Investigation**:
- Conduct security audit
- Review access logs
- Analyze vulnerability
- Implement security fixes

---

## Rollback Testing

### Pre-Deployment Rollback Test

Before deploying streaming feature, test rollback procedure:

1. [ ] Deploy streaming to staging
2. [ ] Execute rollback procedure
3. [ ] Verify rollback successful
4. [ ] Time rollback duration
5. [ ] Document any issues

### Rollback Drill

Conduct regular rollback drills:

1. [ ] Schedule drill (quarterly)
2. [ ] Execute rollback in staging
3. [ ] Verify all steps work
4. [ ] Update procedures if needed
5. [ ] Train team on rollback

## Rollback Communication Template

### Internal Communication

**Subject**: [URGENT] Streaming Feature Rollback - [Date] [Time]

**Body**:
```
Team,

We have initiated a rollback of the streaming feature due to [reason].

Status: [In Progress / Complete]
Rollback Method: [Quick / Full / Database]
Expected Completion: [Time]

Current Metrics:
- Error Rate: [X%]
- Success Rate: [X%]
- TTFC: [X seconds]

Actions Taken:
1. [Action 1]
2. [Action 2]
3. [Action 3]

Next Steps:
1. [Next step 1]
2. [Next step 2]

Point of Contact: [Name] - [Email] - [Phone]

Updates will be provided every 15 minutes.
```

### External Communication (if needed)

**Subject**: Service Update - [Date] [Time]

**Body**:
```
Dear Users,

We have temporarily disabled a new feature to ensure optimal system performance.

Impact: Minimal - All core functionality remains available
Duration: [Estimated time]

We apologize for any inconvenience and appreciate your patience.

For questions, please contact support@chatbi.com

Thank you,
ChatBI Team
```

## Rollback Metrics

Track these metrics during rollback:

| Metric | Before Rollback | After Rollback | Target |
|--------|----------------|----------------|--------|
| Error Rate | [X%] | [X%] | < 5% |
| Success Rate | [X%] | [X%] | > 95% |
| TTFC | [X seconds] | [X seconds] | < 3s |
| Response Time | [X ms] | [X ms] | < 500ms |
| Active Users | [X] | [X] | Stable |

## Lessons Learned Template

After each rollback, document lessons learned:

### Incident Summary
- **Date**: [Date]
- **Duration**: [Duration]
- **Impact**: [Impact description]
- **Root Cause**: [Root cause]

### What Went Wrong
1. [Issue 1]
2. [Issue 2]
3. [Issue 3]

### What Went Right
1. [Success 1]
2. [Success 2]
3. [Success 3]

### Action Items
1. [ ] [Action item 1] - Owner: [Name] - Due: [Date]
2. [ ] [Action item 2] - Owner: [Name] - Due: [Date]
3. [ ] [Action item 3] - Owner: [Name] - Due: [Date]

### Improvements
1. [Improvement 1]
2. [Improvement 2]
3. [Improvement 3]

## Emergency Contacts

- **Deployment Lead**: [Name] - [Phone] - [Email]
- **Backend Engineer**: [Name] - [Phone] - [Email]
- **Frontend Engineer**: [Name] - [Phone] - [Email]
- **DevOps Engineer**: [Name] - [Phone] - [Email]
- **On-Call Engineer**: [Name] - [Phone] - [Email]
- **CTO**: [Name] - [Phone] - [Email]

## Rollback Authority

The following individuals have authority to initiate rollback:

1. Deployment Lead
2. On-Call Engineer
3. Engineering Manager
4. CTO

**Rollback Decision**: Can be made by any of the above without additional approval if critical thresholds are met.

---

**Version**: 1.0.0  
**Last Updated**: February 10, 2026  
**Next Review**: March 10, 2026  
**Last Tested**: [Date]
