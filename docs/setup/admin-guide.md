# 管理员指南

本指南面向系统管理员，介绍如何管理和维护 Digital Store Bot v2。

## 🔑 管理员权限

### 获取管理员权限

1. 在 `config/settings.yml` 中配置您的 Telegram ID：

```yaml
bot:
  admin_ids: 
    - 123456789  # 您的 Telegram 用户 ID
    - 987654321  # 其他管理员 ID
```

2. 重启机器人使配置生效

### 管理员命令

管理员在 Telegram 中可使用特殊命令：

- `/admin` - 进入管理员模式
- `/stats` - 查看系统统计
- `/users` - 用户管理
- `/orders` - 订单管理
- `/products` - 产品管理

## 🖥️ Web 管理面板

### 访问管理面板

1. 启动 Web 管理服务：

```bash
# 开发环境
poetry run python src/presentation/web/admin_main.py

# 生产环境 (Docker)
docker compose up admin -d
```

2. 访问 `http://localhost:8080/admin`

### 面板功能

- **📊 数据仪表板** - 实时统计和图表
- **👥 用户管理** - 用户信息和权限管理
- **📦 产品管理** - 产品上架、编辑、下架
- **💰 订单管理** - 订单状态和退款处理
- **💳 支付管理** - 支付网关和交易记录
- **🔗 推荐管理** - 推荐关系和佣金管理

## 👥 用户管理

### 查看用户信息

通过 Web 面板或 Telegram 命令：

```
/users list - 显示用户列表
/users info <user_id> - 查看特定用户详情
/users search <keyword> - 搜索用户
```

### 用户操作

- **禁用用户**: 暂停用户访问权限
- **重置密码**: 重置用户账户
- **余额调整**: 手动调整用户余额
- **订单历史**: 查看用户购买记录

### 批量操作

- 导出用户数据
- 批量发送通知
- 用户数据统计分析

## 📦 产品管理

### 产品配置文件

产品信息存储在 `data/products.json`：

```json
{
  "categories": [
    {
      "id": "software",
      "name": "软件许可",
      "description": "各类软件和工具",
      "emoji": "💻"
    }
  ],
  "products": [
    {
      "id": "premium_1month",
      "name": "高级会员 - 1个月",
      "description": "享受所有高级功能",
      "category_id": "software",
      "price": 9.99,
      "currency": "USD",
      "duration_days": 30,
      "is_active": true,
      "stock": 1000
    }
  ]
}
```

### 产品操作

- **添加产品**: 在 JSON 文件中添加新产品
- **编辑产品**: 修改价格、描述等信息
- **库存管理**: 调整产品库存数量
- **上架/下架**: 控制产品显示状态

### 热重载配置

修改产品配置后无需重启：

```bash
# 重新加载产品配置
curl -X POST http://localhost:8080/admin/reload-products
```

## 💰 订单管理

### 订单状态

- **待支付** (pending) - 订单已创建，等待支付
- **已支付** (paid) - 支付成功，等待发货
- **已完成** (completed) - 订单已发货完成
- **已取消** (cancelled) - 订单已取消
- **已退款** (refunded) - 订单已退款

### 订单处理

```bash
# 查看订单列表
/orders list

# 订单详情
/orders info <order_id>

# 手动完成订单
/orders complete <order_id>

# 退款处理
/orders refund <order_id>
```

### 批量处理

- 导出订单数据
- 批量状态更新
- 财务对账报告

## 💳 支付管理

### 支付网关配置

#### Cryptomus 配置

```yaml
payments:
  cryptomus:
    enabled: true
    merchant_id: "your_merchant_id"
    api_key: "your_api_key"
    webhook_secret: "your_webhook_secret"
```

#### Telegram Stars 配置

```yaml
payments:
  telegram_stars:
    enabled: true
    provider_token: "your_provider_token"
```

### 支付监控

- 实时支付状态监控
- 失败支付分析
- 支付网关性能统计
- 财务报表生成

## 🔗 推荐系统管理

### 推荐设置

```yaml
referral:
  enabled: true
  level_one_reward_rate: 0.10  # 一级推荐 10%
  level_two_reward_rate: 0.05  # 二级推荐 5%
  bonus_devices_count: 1       # 奖励设备数量
```

### 推荐数据

- 推荐关系链查看
- 佣金计算和发放
- 推荐效果分析
- 反作弊检测

## 📊 监控和统计

### 系统监控

```bash
# 检查系统健康状态
./scripts/healthcheck.sh

# 详细服务状态
python3 scripts/check_services.py

# 查看系统日志
tail -f logs/app.log
```

### 关键指标

- **用户指标**: 注册数、活跃用户、留存率
- **业务指标**: 订单量、收入、转化率
- **技术指标**: 响应时间、错误率、可用性

### 报警设置

配置监控报警：

- 系统故障自动通知
- 业务异常指标报警
- 支付失败率超阈值

## 🗄️ 数据库管理

### 数据库迁移

```bash
# 创建新迁移
poetry run python -m src.infrastructure.database.migrations.migration_manager create "迁移描述"

# 应用迁移
poetry run python -m src.infrastructure.database.migrations.migration_manager upgrade

# 回滚迁移
poetry run python -m src.infrastructure.database.migrations.migration_manager downgrade
```

### 数据备份

```bash
# 手动备份
./scripts/backup-database.sh

# 自动备份 (cron job)
0 2 * * * /path/to/scripts/backup-database.sh
```

### 数据恢复

```bash
# 从备份恢复
./scripts/restore-database.sh backup_file.sql
```

## 🔒 安全管理

### 访问控制

- 定期更新管理员列表
- 监控异常管理操作
- 实施最小权限原则

### 数据保护

- 敏感数据加密存储
- 定期安全审计
- 合规性检查

### 日志审计

- 所有管理操作记录日志
- 异常访问检测
- 安全事件响应

## 🚨 故障处理

### 常见问题

#### 机器人无响应
1. 检查服务进程状态
2. 验证 Bot Token 有效性
3. 检查网络连接

#### 支付失败
1. 检查支付网关配置
2. 验证 Webhook 回调
3. 查看支付日志

#### 数据库错误
1. 检查数据库连接
2. 验证迁移状态
3. 检查磁盘空间

### 应急处理

```bash
# 快速重启服务
docker compose restart bot

# 紧急维护模式
echo "maintenance" > /tmp/maintenance.flag

# 恢复正常服务
rm /tmp/maintenance.flag
```

## 📋 维护清单

### 日常维护

- [ ] 检查系统日志
- [ ] 监控关键指标
- [ ] 验证备份状态
- [ ] 更新安全补丁

### 周期维护

- [ ] 数据库性能优化
- [ ] 清理过期数据
- [ ] 更新依赖包
- [ ] 安全审计

### 版本更新

- [ ] 备份当前版本
- [ ] 测试新版本
- [ ] 灰度发布
- [ ] 全量部署

## 📞 技术支持

如需技术支持：

- 📧 技术邮箱: tech@digitalstore.com
- 🔧 紧急联系: +1-xxx-xxx-xxxx
- 📖 技术文档: [开发指南](../development/CLAUDE.md)

---

🛡️ 系统安全和稳定运行是我们的首要任务，如有任何疑问请及时联系技术团队。