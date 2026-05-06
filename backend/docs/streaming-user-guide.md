# Streaming User Guide

## What is Streaming?

Streaming is a feature that shows you the AI's thinking process in real-time. Instead of waiting for the entire response, you see each processing stage appear progressively as the AI generates content.

## User Experience

### Before Streaming

Previously, when you submitted a query:
1. You saw a loading indicator
2. You waited for the entire process to complete
3. All results appeared at once

### With Streaming

Now, when you submit a query:
1. Each processing stage appears sequentially
2. Content streams in progressively as the AI generates it
3. You see exactly what the AI is thinking in real-time
4. You get immediate feedback that the system is working

## Processing Stages

When you submit a query, you'll see these stages appear in order:

### 1. 意图识别 (Intent Recognition)
**What it does**: Understands what you're asking for

**What you'll see**:
- Stage appears with title "意图识别"
- Content streams in showing the AI's analysis
- Final result shows query type and key entities

**Example**:
```
意图识别
正在分析您的问题...
**查询类型**: 订单统计
**关键实体**: 张三
**时间范围**: 无
```

### 2. 表选择 (Table Selection)
**What it does**: Identifies which database tables are needed

**What you'll see**:
- Stage appears instantly (no streaming, rule-based)
- Shows selected tables and their relevance

**Example**:
```
表选择
**已选择的表**:
- orders (订单表) - 相关度: 95%
- customers (客户表) - 相关度: 80%
```

### 3. SQL生成 (SQL Generation)
**What it does**: Generates the SQL query

**What you'll see**:
- Stage appears with title "SQL生成"
- SQL code streams in progressively
- Final result shows formatted SQL

**Example**:
```
SQL生成
正在生成SQL查询...
```sql
SELECT customer_name, COUNT(*) as order_count
FROM orders
WHERE customer_name = '张三'
GROUP BY customer_name
```
```

### 4. SQL执行 (SQL Execution)
**What it does**: Runs the query against the database

**What you'll see**:
- Stage appears instantly (no streaming, database operation)
- Shows query results in table format

**Example**:
```
SQL执行
**查询结果**:
| 客户名称 | 订单数量 |
|---------|---------|
| 张三     | 5       |
```

### 5. 数据分析 (Data Analysis)
**What it does**: Analyzes the results and provides insights

**What you'll see**:
- Stage appears with title "数据分析"
- Analysis streams in progressively
- Final result shows insights and recommendations

**Example**:
```
数据分析
正在分析数据...
根据查询结果，张三共下了5单。这个订单量处于中等水平...
```

## Visual Indicators

### Streaming Indicator
When a stage is actively streaming content, you'll see:
- ⏳ Hourglass icon next to the stage name
- Three animated dots (⋯) at the bottom of the stage content
- Content appearing progressively

### Completion Indicator
When a stage completes, you'll see:
- ✅ Checkmark icon next to the stage name
- Stage automatically collapses (you can expand it again)
- No more content updates

### Error Indicator
If a stage encounters an error, you'll see:
- ❌ Error icon next to the stage name
- Error message in the stage content
- Option to retry the query

## Interacting with Stages

### Expanding/Collapsing Stages

**To collapse a stage**:
- Click on the stage header
- Stage content will smoothly collapse

**To expand a stage**:
- Click on the collapsed stage header
- Stage content will smoothly expand

**Tip**: Completed stages automatically collapse to keep the interface clean, but you can always expand them to review the details.

### Scrolling During Streaming

- The interface automatically scrolls to show new content as it streams in
- You can manually scroll up to review previous stages
- Scrolling won't interrupt the streaming process

### Submitting New Queries

- You can submit a new query while streaming is in progress
- The current streaming will complete before the new query starts
- Each query maintains its own set of stages

## Performance

### Streaming Speed

- Content streams at a natural reading pace
- Typical time to first chunk: < 3 seconds
- Total streaming duration varies by stage complexity

### Responsiveness

- The UI remains responsive during streaming
- You can scroll, collapse/expand stages, and navigate the interface
- Streaming happens in the background without blocking interactions

## Troubleshooting

### Issue: Content appears all at once

**Possible causes**:
- Streaming is disabled in configuration
- Network connection is slow
- AI model doesn't support streaming

**What to do**:
- Check your internet connection
- Refresh the page
- Contact support if issue persists

### Issue: Stage stuck in loading state

**Possible causes**:
- Network connection interrupted
- AI model timeout
- Backend error

**What to do**:
- Wait 60 seconds (timeout period)
- Refresh the page if stage doesn't complete
- Try submitting the query again
- Check browser console for errors (F12)

### Issue: Content appears jumbled

**Possible causes**:
- Browser cache issue
- WebSocket connection problem

**What to do**:
- Refresh the page (Ctrl+F5 or Cmd+Shift+R)
- Clear browser cache
- Try a different browser

## Tips for Best Experience

### 1. Use a Modern Browser
- Chrome, Firefox, Safari, or Edge (latest versions)
- Ensure JavaScript is enabled
- Disable browser extensions that might interfere with WebSockets

### 2. Stable Internet Connection
- Streaming works best with a stable connection
- Slow connections may cause delays but won't break functionality
- Mobile connections work fine

### 3. Watch the Stages
- Pay attention to each stage to understand the AI's process
- Expand stages to see detailed information
- Use this information to refine your queries

### 4. Be Patient
- Some queries take longer than others
- Complex queries may have longer streaming times
- The system is working even if content streams slowly

## Privacy and Security

### Data Handling
- All streaming data is encrypted (WSS protocol)
- No data is stored during streaming
- Session data follows existing privacy policies

### Security
- Streaming uses secure WebSocket connections
- Authentication is required for all queries
- Rate limiting prevents abuse

## Feedback

We're continuously improving the streaming experience. If you encounter issues or have suggestions:

1. Check the troubleshooting section above
2. Review browser console for errors (F12)
3. Contact support with:
   - Your query text
   - Which stage had issues
   - Browser and version
   - Screenshots if possible

## Advanced Features

### Keyboard Shortcuts

- **Enter**: Submit query
- **Esc**: Cancel current query (if supported)
- **Space**: Expand/collapse focused stage

### Accessibility

- Screen reader support for stage updates
- Keyboard navigation for all interactions
- High contrast mode compatible
- Respects reduced motion preferences

## FAQ

**Q: Can I disable streaming?**
A: Streaming is enabled by default for the best experience. Contact your administrator if you need to disable it.

**Q: Why do some stages stream and others don't?**
A: Only AI-generated stages (Intent Recognition, SQL Generation, Data Analysis) use streaming. Rule-based stages (Table Selection) and database operations (SQL Execution) appear instantly.

**Q: Does streaming use more data?**
A: No, streaming uses the same amount of data. It just delivers it progressively instead of all at once.

**Q: Can I copy content while it's streaming?**
A: Yes, you can select and copy content at any time, even while streaming is in progress.

**Q: What happens if I close the browser during streaming?**
A: The streaming will stop, but your session is preserved. When you return, you can submit the query again.

**Q: Is streaming available on mobile?**
A: Yes, streaming works on mobile browsers with the same functionality as desktop.

## Version Information

- **Current Version**: 1.0.0
- **Release Date**: February 10, 2026
- **Compatibility**: All modern browsers
- **Requirements**: JavaScript enabled, WebSocket support

---

**Need Help?**

If you have questions or encounter issues not covered in this guide, please contact support or refer to the technical documentation.
