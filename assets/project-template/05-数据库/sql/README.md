# SQL文件目录

> **数据库SQL文件存放位置**

---

## 📋 文件说明

### 文件命名规范
```
格式：[日期]_[操作]_[表名].sql
示例：20251027_create_users.sql
      20251028_alter_orders.sql
```

### 文件内容
- 每个SQL文件包含完整的SQL语句
- 包含必要的注释说明
- 可以独立执行

---

## 📁 文件列表

### 初始化SQL
- `init_tables.sql` - 数据库初始化（创建所有表）

### 变更SQL（按日期排序）
- `20251027_create_users.sql` - 创建用户表
- `20251028_create_orders.sql` - 创建订单表
- ...（按时间顺序添加）

---

## 🔧 使用方法

### 初始化数据库
```bash
# MySQL
mysql -u root -p database_name < init_tables.sql

# Docker环境
docker-compose exec db mysql -u root -p database_name < init_tables.sql
```

### 执行迁移SQL
```bash
# 按顺序执行变更SQL
mysql -u root -p database_name < 20251027_create_users.sql
mysql -u root -p database_name < 20251028_create_orders.sql
```

---

## 📝 注意事项

1. **文件命名**：必须包含日期，便于追溯
2. **独立执行**：每个SQL文件应该可以独立执行
3. **幂等性**：建议使用 `IF NOT EXISTS` 等语句
4. **注释**：复杂SQL必须添加注释说明

---

**最后更新**：[日期]

