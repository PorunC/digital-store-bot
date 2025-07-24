# 常见问题 FAQ

这里收集了用户和开发者最常遇到的问题及解决方案。

## 🚀 安装和部署

### Q: Poetry 安装失败怎么办？

**A:** 尝试以下解决方案：

```bash
# 方法 1: 使用官方安装脚本
curl -sSL https://install.python-poetry.org | python3 -

# 方法 2: 通过 pip 安装
pip install poetry

# 方法 3: 使用系统包管理器
# Ubuntu/Debian
sudo apt install python3-poetry

# macOS
brew install poetry
```

### Q: Docker 部署时端口冲突怎么办？

**A:** 修改 `docker-compose.yml` 中的端口映射：

```yaml
services:
  bot:
    ports:
      - "8081:8080"  # 改为其他可用端口
```

### Q: 数据库迁移失败？

**A:** 按以下步骤排查：

1. 检查数据库连接配置
2. 确保数据库服务正在运行
3. 验证用户权限是否足够
4. 查看详细错误日志

```bash
# 检查迁移状态
poetry run python -m src.infrastructure.database.migrations.migration_manager status

# 重置迁移（慎用）
poetry run python -m src.infrastructure.database.migrations.migration_manager reset
```

## 🤖 机器人使用

### Q: 机器人没有响应消息？

**A:** 检查以下几点：

1. **验证 Bot Token**：
   ```bash
   curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"
   ```

2. **检查网络连接**：
   ```bash
   ping api.telegram.org
   ```

3. **查看日志文件**：
   ```bash
   tail -f logs/app.log
   ```

4. **重启机器人服务**：
   ```bash
   docker compose restart bot
   ```

### Q: 支付失败怎么处理？

**A:** 根据支付方式排查：

**Telegram Stars 支付**：
- 确认 provider_token 配置正确
- 检查用户 Telegram 账户余额
- 验证支付金额是否在允许范围

**Cryptomus 支付**：
- 验证 merchant_id 和 api_key
- 检查 webhook URL 是否可访问
- 确认支付网关服务状态

### Q: 如何查看用户的购买历史？

**A:** 管理员可以通过以下方式查看：

1. **Telegram 命令**：
   ```
   /users info <user_id>
   /orders list user:<user_id>
   ```

2. **Web 管理面板**：
   访问 `/admin/users/<user_id>/orders`

3. **数据库查询**：
   ```sql
   SELECT * FROM orders WHERE user_id = '<user_id>';
   ```

## ⚙️ 配置问题

### Q: 如何修改机器人的显示语言？

**A:** 有两种方式：

1. **用户端切换**：
   - 在机器人中点击"设置"
   - 选择"语言设置"
   - 选择偏好语言

2. **系统默认语言**：
   ```yaml
   # config/settings.yml
   localization:
     default_language: "zh"  # zh, en, ru
   ```

### Q: 推荐系统佣金比例如何调整？

**A:** 在配置文件中修改：

```yaml
# config/settings.yml
referral:
  level_one_reward_rate: 0.15  # 一级推荐 15%
  level_two_reward_rate: 0.08  # 二级推荐 8%
```

修改后重启服务生效。

### Q: 如何添加新的支付网关？

**A:** 按以下步骤添加：

1. **实现支付网关接口**：
   ```python
   # src/infrastructure/external/payment_gateways/your_gateway.py
   class YourPaymentGateway(PaymentGateway):
       async def create_payment(self, amount, currency, order_id):
           # 实现支付创建逻辑
           pass
   ```

2. **注册到工厂**：
   ```python
   # src/infrastructure/external/payment_gateways/factory.py
   def create_payment_gateway(gateway_type: str):
       if gateway_type == "your_gateway":
           return YourPaymentGateway()
   ```

3. **添加配置**：
   ```yaml
   payments:
     your_gateway:
       enabled: true
       api_key: "your_api_key"
   ```

## 🔧 开发问题

### Q: 如何运行特定的测试？

**A:** 使用 pytest 的各种选项：

```bash
# 运行单个测试文件
poetry run pytest tests/unit/domain/test_user.py

# 运行特定测试类
poetry run pytest tests/unit/domain/test_user.py::TestUser

# 运行特定测试方法
poetry run pytest tests/unit/domain/test_user.py::TestUser::test_create_user

# 按标记运行测试
poetry run pytest -m "unit"
poetry run pytest -m "integration"
poetry run pytest -m "not slow"

# 运行匹配模式的测试
poetry run pytest -k "test_payment"
```

### Q: 如何添加新的域事件？

**A:** 按 DDD 模式添加：

1. **创建事件类**：
   ```python
   # src/domain/events/your_events.py
   @dataclass(frozen=True)
   class YourEvent(DomainEvent):
       entity_id: str
       data: Dict[str, Any]
   ```

2. **在实体中发布事件**：
   ```python
   # src/domain/entities/your_entity.py
   def some_action(self):
       # 业务逻辑
       event = YourEvent.create(entity_id=self.id, data={})
       self.add_domain_event(event)
   ```

3. **创建事件处理器**：
   ```python
   # src/application/handlers/your_handlers.py
   @event_handler("YourEvent")
   class YourEventHandler:
       async def handle(self, event: YourEvent):
           # 处理事件逻辑
           pass
   ```

### Q: 数据库查询性能优化？

**A:** 采用以下优化策略：

1. **添加索引**：
   ```python
   # 在迁移中添加索引
   op.create_index('ix_users_telegram_id', 'users', ['telegram_id'])
   ```

2. **使用查询优化**：
   ```python
   # 预加载关联数据
   users = await session.execute(
       select(User).options(selectinload(User.orders))
   )
   ```

3. **分页查询**：
   ```python
   # 限制查询结果数量
   query = select(User).limit(50).offset(page * 50)
   ```

## 🔒 安全问题

### Q: 如何保护敏感配置信息？

**A:** 使用环境变量和加密：

1. **使用环境变量**：
   ```bash
   # .env 文件
   BOT_TOKEN="your_secret_token"
   DATABASE_PASSWORD="your_db_password"
   ```

2. **加密存储**：
   ```python
   # 使用 cryptography 库加密敏感数据
   from cryptography.fernet import Fernet
   
   key = Fernet.generate_key()
   cipher = Fernet(key)
   encrypted_data = cipher.encrypt(b"sensitive_data")
   ```

3. **文件权限控制**：
   ```bash
   chmod 600 config/settings.yml
   chmod 600 .env
   ```

### Q: 如何防止重复支付？

**A:** 实现幂等性检查：

1. **订单状态检查**：
   ```python
   if order.status != OrderStatus.PENDING:
       raise PaymentAlreadyProcessed()
   ```

2. **支付锁机制**：
   ```python
   async with payment_lock(order_id):
       # 支付处理逻辑
       pass
   ```

3. **交易ID去重**：
   ```python
   existing_payment = await payment_repo.get_by_transaction_id(tx_id)
   if existing_payment:
       return existing_payment
   ```

## 🛠️ 运维问题

### Q: 如何监控系统健康状态？

**A:** 使用多层监控：

1. **应用健康检查**：
   ```bash
   # 检查服务状态
   ./scripts/healthcheck.sh
   
   # 详细系统检查
   python3 scripts/check_services.py
   ```

2. **日志监控**：
   ```bash
   # 实时查看错误日志
   tail -f logs/app.log | grep ERROR
   
   # 分析错误统计
   grep ERROR logs/app.log | wc -l
   ```

3. **资源监控**：
   ```bash
   # 内存使用情况
   docker stats
   
   # 磁盘空间
   df -h
   ```

### Q: 如何处理大量并发用户？

**A:** 采用以下扩展策略：

1. **水平扩展**：
   ```yaml
   # docker-compose.yml
   services:
     bot:
       deploy:
         replicas: 3
   ```

2. **连接池优化**：
   ```yaml
   database:
     pool_size: 20
     max_overflow: 30
   ```

3. **缓存策略**：
   ```python
   # 使用 Redis 缓存热点数据
   @cached(ttl=300)
   async def get_popular_products():
       return await product_service.get_popular()
   ```

### Q: 数据备份和恢复策略？

**A:** 实施多层备份：

1. **自动备份脚本**：
   ```bash
   # 每日自动备份
   0 2 * * * /app/scripts/backup-database.sh
   ```

2. **多地备份**：
   ```bash
   # 备份到云存储
   aws s3 cp backup.sql s3://your-backup-bucket/
   ```

3. **恢复测试**：
   ```bash
   # 定期测试恢复流程
   ./scripts/test-restore.sh
   ```

## 📞 获取更多帮助

如果以上 FAQ 无法解决您的问题：

1. **搜索 Issues**: [GitHub Issues](https://github.com/your-org/digital-store-bot-v2/issues)
2. **查看文档**: [完整文档](../README.md)
3. **社区讨论**: [GitHub Discussions](https://github.com/your-org/digital-store-bot-v2/discussions)
4. **联系支持**: support@digitalstore.com

---

💡 **提示**: 遇到新问题时，请先查看日志文件，大多数问题都能从日志中找到线索！