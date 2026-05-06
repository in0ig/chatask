# Streaming Feature Deployment Checklist

## Pre-Deployment Checklist

### Code Quality

- [ ] All unit tests pass (100% pass rate)
  - [ ] Backend: `pytest backend/tests/unit/ -v`
  - [ ] Frontend: `npm run test -- --run`

- [ ] All property-based tests pass (100+ iterations each)
  - [ ] Backend: `pytest backend/tests/unit/test_*_properties.py -v`
  - [ ] Frontend: `npm run test -- --run tests/unit/store/chat.streaming-properties.test.ts`

- [ ] All integration tests pass
  - [ ] Backend: `pytest backend/tests/integration/ -v`

- [ ] Performance tests meet requirements
  - [ ] TTFC < 3 seconds
  - [ ] Chunk delivery rate: 50-200ms
  - [ ] Total duration < 30 seconds per stage

- [ ] No TypeScript errors
  - [ ] Frontend: `npx tsc --noEmit`

- [ ] No linting errors
  - [ ] Backend: `flake8 backend/src/`
  - [ ] Frontend: `npm run lint`

- [ ] Code review completed and approved
  - [ ] At least 2 reviewers
  - [ ] All comments addressed

### Documentation

- [ ] API documentation updated
  - [ ] `backend/docs/streaming-api-documentation.md` reviewed
  - [ ] All endpoints documented
  - [ ] Examples provided

- [ ] User guide created
  - [ ] `backend/docs/streaming-user-guide.md` reviewed
  - [ ] Screenshots added
  - [ ] FAQ section complete

- [ ] Monitoring and logging guide created
  - [ ] `backend/docs/streaming-monitoring-logging.md` reviewed
  - [ ] Metrics defined
  - [ ] Alert rules configured

- [ ] Deployment checklist created
  - [ ] This document reviewed
  - [ ] All steps verified

- [ ] Rollback plan created
  - [ ] `backend/docs/streaming-rollback-plan.md` reviewed
  - [ ] Rollback steps tested

### Configuration

- [ ] Environment variables configured
  - [ ] Backend: `ENABLE_STREAMING=true` in `.env`
  - [ ] Frontend: `VITE_ENABLE_STREAMING=true` in `.env`
  - [ ] Production values verified

- [ ] WebSocket configuration verified
  - [ ] WSS (secure WebSocket) enabled in production
  - [ ] CORS settings configured
  - [ ] Timeout settings appropriate (60 seconds)

- [ ] AI model configuration verified
  - [ ] Cloud model (Qwen) streaming enabled
  - [ ] Local model (OpenAI) streaming enabled
  - [ ] API keys valid and tested

- [ ] Database configuration verified
  - [ ] Connection pool size adequate
  - [ ] Query timeout settings appropriate

### Infrastructure

- [ ] Server resources adequate
  - [ ] CPU: Sufficient for concurrent streaming
  - [ ] Memory: Adequate for WebSocket connections
  - [ ] Network: Bandwidth sufficient for streaming

- [ ] Load balancer configured
  - [ ] WebSocket support enabled
  - [ ] Sticky sessions configured (if needed)
  - [ ] Health checks configured

- [ ] CDN configured (if applicable)
  - [ ] WebSocket traffic allowed
  - [ ] Caching rules updated

- [ ] Monitoring tools configured
  - [ ] Prometheus metrics collection
  - [ ] Grafana dashboards created
  - [ ] Alert rules configured

### Security

- [ ] Security review completed
  - [ ] WebSocket security verified (WSS)
  - [ ] Authentication/authorization tested
  - [ ] Rate limiting configured

- [ ] Content validation implemented
  - [ ] XSS protection verified
  - [ ] Input sanitization tested
  - [ ] Output encoding verified

- [ ] Secrets management verified
  - [ ] API keys stored securely
  - [ ] Environment variables not exposed
  - [ ] Secrets rotation plan in place

### Testing

- [ ] Browser verification completed
  - [ ] Chrome: Tested and verified
  - [ ] Firefox: Tested and verified
  - [ ] Safari: Tested and verified
  - [ ] Edge: Tested and verified
  - [ ] Mobile browsers: Tested and verified

- [ ] End-to-end testing completed
  - [ ] Happy path: Query submission to completion
  - [ ] Error scenarios: Interruption, timeout, fallback
  - [ ] Edge cases: Empty content, large responses

- [ ] Load testing completed
  - [ ] 100 concurrent users tested
  - [ ] Performance metrics within targets
  - [ ] No memory leaks detected

- [ ] Backward compatibility verified
  - [ ] Non-streaming stages still work
  - [ ] Existing API contracts maintained
  - [ ] Old clients still supported

### Backup and Recovery

- [ ] Database backup verified
  - [ ] Recent backup available
  - [ ] Restore procedure tested

- [ ] Configuration backup created
  - [ ] Current configuration saved
  - [ ] Rollback configuration prepared

- [ ] Rollback plan tested
  - [ ] Rollback steps verified
  - [ ] Rollback time estimated (< 5 minutes)

## Deployment Steps

### Step 1: Pre-Deployment Verification

**Time**: 30 minutes before deployment

1. [ ] Verify all pre-deployment checklist items completed
2. [ ] Run final test suite
   ```bash
   # Backend
   cd backend
   pytest tests/ -v
   
   # Frontend
   cd frontend
   npm run test -- --run
   ```
3. [ ] Verify staging environment matches production
4. [ ] Notify team of upcoming deployment

### Step 2: Database Migration (if needed)

**Time**: 15 minutes before deployment

1. [ ] Backup production database
   ```bash
   ./scripts/backup_database.sh
   ```
2. [ ] Run database migrations (if any)
   ```bash
   cd backend
   alembic upgrade head
   ```
3. [ ] Verify migration success
4. [ ] Test database connectivity

### Step 3: Backend Deployment

**Time**: Deployment start

1. [ ] Enable maintenance mode (optional)
   ```bash
   ./scripts/enable_maintenance_mode.sh
   ```

2. [ ] Deploy backend code
   ```bash
   # Pull latest code
   git pull origin main
   
   # Install dependencies
   cd backend
   pip install -r requirements.txt
   
   # Restart backend service
   sudo systemctl restart chatbi-backend
   ```

3. [ ] Verify backend health
   ```bash
   curl http://localhost:8000/health
   ```

4. [ ] Check backend logs
   ```bash
   tail -f /var/log/chatbi/backend.log
   ```

5. [ ] Verify WebSocket endpoint
   ```bash
   # Test WebSocket connection
   wscat -c ws://localhost:8000/ws
   ```

### Step 4: Frontend Deployment

**Time**: 5 minutes after backend deployment

1. [ ] Build frontend
   ```bash
   cd frontend
   npm run build
   ```

2. [ ] Deploy frontend assets
   ```bash
   # Copy build to web server
   sudo cp -r dist/* /var/www/chatbi/
   ```

3. [ ] Clear CDN cache (if applicable)
   ```bash
   ./scripts/clear_cdn_cache.sh
   ```

4. [ ] Verify frontend loads
   ```bash
   curl http://localhost:5173/
   ```

### Step 5: Configuration Update

**Time**: Immediately after deployment

1. [ ] Update environment variables
   ```bash
   # Backend
   echo "ENABLE_STREAMING=true" >> backend/.env
   
   # Frontend
   echo "VITE_ENABLE_STREAMING=true" >> frontend/.env
   ```

2. [ ] Restart services to apply configuration
   ```bash
   sudo systemctl restart chatbi-backend
   sudo systemctl restart chatbi-frontend
   ```

3. [ ] Verify configuration loaded
   ```bash
   # Check backend logs for streaming enabled message
   grep "Streaming enabled" /var/log/chatbi/backend.log
   ```

### Step 6: Smoke Testing

**Time**: 10 minutes after deployment

1. [ ] Test basic query submission
   - Submit query: "张三下了几单"
   - Verify all stages appear
   - Verify content streams progressively

2. [ ] Test error handling
   - Submit invalid query
   - Verify error message appears
   - Verify system recovers

3. [ ] Test WebSocket connection
   - Open browser console
   - Verify WebSocket connection established
   - Verify no errors in console

4. [ ] Test stage interactions
   - Collapse/expand stages
   - Scroll during streaming
   - Submit multiple queries

### Step 7: Monitoring Setup

**Time**: 15 minutes after deployment

1. [ ] Verify monitoring dashboards
   - Open Grafana dashboard
   - Verify metrics flowing
   - Check for anomalies

2. [ ] Verify alerting
   - Test alert rules
   - Verify notifications working
   - Check alert thresholds

3. [ ] Check log aggregation
   - Verify logs flowing to ELK
   - Check log volume
   - Verify log format

### Step 8: Gradual Rollout (Optional)

**Time**: 30 minutes after deployment

1. [ ] Enable streaming for 10% of users
   ```python
   # Feature flag configuration
   STREAMING_ROLLOUT_PERCENTAGE = 10
   ```

2. [ ] Monitor metrics for 15 minutes
   - Check error rates
   - Verify performance
   - Monitor user feedback

3. [ ] Increase to 50% if metrics good
   ```python
   STREAMING_ROLLOUT_PERCENTAGE = 50
   ```

4. [ ] Monitor for another 15 minutes

5. [ ] Enable for 100% if all good
   ```python
   STREAMING_ROLLOUT_PERCENTAGE = 100
   ```

### Step 9: Post-Deployment Verification

**Time**: 1 hour after deployment

1. [ ] Run full test suite in production
   ```bash
   # Run smoke tests
   ./scripts/run_smoke_tests.sh
   ```

2. [ ] Verify all metrics within targets
   - TTFC < 3 seconds
   - Success rate > 95%
   - Error rate < 5%

3. [ ] Check for errors in logs
   ```bash
   # Check for errors in last hour
   grep ERROR /var/log/chatbi/backend.log | tail -100
   ```

4. [ ] Verify user feedback
   - Check support tickets
   - Monitor user complaints
   - Review analytics

### Step 10: Disable Maintenance Mode

**Time**: After all verification complete

1. [ ] Disable maintenance mode
   ```bash
   ./scripts/disable_maintenance_mode.sh
   ```

2. [ ] Announce deployment complete
   - Notify team
   - Update status page
   - Send user communication (if needed)

## Post-Deployment Monitoring

### First 24 Hours

- [ ] Monitor metrics every hour
  - TTFC
  - Success rate
  - Error rate
  - WebSocket connections

- [ ] Check logs for errors
  - Review error logs every 2 hours
  - Investigate any anomalies
  - Address critical issues immediately

- [ ] Monitor user feedback
  - Check support tickets
  - Review user complaints
  - Gather feedback from team

### First Week

- [ ] Daily metrics review
  - Compare to baseline
  - Identify trends
  - Address issues proactively

- [ ] Weekly performance review
  - Analyze metrics
  - Identify optimization opportunities
  - Plan improvements

### First Month

- [ ] Weekly metrics review
- [ ] Monthly comprehensive review
- [ ] Gather user feedback
- [ ] Plan optimizations

## Success Criteria

Deployment is considered successful if:

- [ ] All tests pass (100% pass rate)
- [ ] TTFC < 3 seconds (average)
- [ ] Success rate > 95%
- [ ] Error rate < 5%
- [ ] No critical issues reported
- [ ] User feedback positive
- [ ] Performance metrics within targets
- [ ] No rollback required

## Rollback Triggers

Initiate rollback if:

- [ ] Success rate < 80%
- [ ] Error rate > 20%
- [ ] TTFC > 10 seconds (average)
- [ ] Critical security issue discovered
- [ ] Data corruption detected
- [ ] System instability

## Rollback Procedure

If rollback is needed, follow the rollback plan:

1. [ ] Refer to `backend/docs/streaming-rollback-plan.md`
2. [ ] Execute rollback steps
3. [ ] Verify system stability
4. [ ] Investigate root cause
5. [ ] Plan fix and re-deployment

## Communication Plan

### Before Deployment

- [ ] Notify team 24 hours in advance
- [ ] Send deployment schedule
- [ ] Identify on-call personnel

### During Deployment

- [ ] Update status page
- [ ] Send deployment start notification
- [ ] Provide progress updates

### After Deployment

- [ ] Send deployment complete notification
- [ ] Update documentation
- [ ] Share metrics and results

### If Issues Occur

- [ ] Notify team immediately
- [ ] Update status page
- [ ] Communicate with users (if needed)
- [ ] Provide regular updates

## Team Responsibilities

### Deployment Lead
- [ ] Coordinate deployment
- [ ] Execute deployment steps
- [ ] Make go/no-go decisions

### Backend Engineer
- [ ] Deploy backend code
- [ ] Verify backend health
- [ ] Monitor backend logs

### Frontend Engineer
- [ ] Deploy frontend code
- [ ] Verify frontend health
- [ ] Monitor browser console

### DevOps Engineer
- [ ] Manage infrastructure
- [ ] Configure monitoring
- [ ] Handle rollback if needed

### QA Engineer
- [ ] Execute smoke tests
- [ ] Verify functionality
- [ ] Report issues

### Product Manager
- [ ] Communicate with stakeholders
- [ ] Monitor user feedback
- [ ] Make business decisions

## Emergency Contacts

- **Deployment Lead**: [Name] - [Phone] - [Email]
- **Backend Engineer**: [Name] - [Phone] - [Email]
- **Frontend Engineer**: [Name] - [Phone] - [Email]
- **DevOps Engineer**: [Name] - [Phone] - [Email]
- **On-Call Engineer**: [Name] - [Phone] - [Email]

## Notes

- Deployment window: [Date] [Time] - [Time]
- Expected downtime: 0 minutes (rolling deployment)
- Rollback time: < 5 minutes
- Support coverage: 24/7 for first 48 hours

---

**Deployment Date**: _______________  
**Deployment Lead**: _______________  
**Sign-off**: _______________

**Version**: 1.0.0  
**Last Updated**: February 10, 2026
