#!/bin/bash

# AWS 部署辅助脚本
# 使用方法: ./scripts/deploy-to-aws.sh [setup|build|deploy|init-db]

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置变量（请根据实际情况修改）
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "YOUR_ACCOUNT_ID")
ECR_REPOSITORY="knowledgehub-backend"
ECS_CLUSTER="knowledgehub-cluster"
ECS_SERVICE="knowledgehub-backend-service"
TASK_DEFINITION="knowledgehub-backend"

# 检查 AWS CLI 是否安装
check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}错误: AWS CLI 未安装。请先安装 AWS CLI。${NC}"
        exit 1
    fi
}

# 检查 Docker 是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}错误: Docker 未安装。请先安装 Docker。${NC}"
        exit 1
    fi
}

# 设置 ECR 仓库
setup_ecr() {
    echo -e "${GREEN}正在创建 ECR 仓库...${NC}"
    
    if aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION &> /dev/null; then
        echo -e "${YELLOW}ECR 仓库已存在，跳过创建。${NC}"
    else
        aws ecr create-repository \
            --repository-name $ECR_REPOSITORY \
            --region $AWS_REGION
        echo -e "${GREEN}ECR 仓库创建成功！${NC}"
    fi
    
    # 登录 ECR
    echo -e "${GREEN}正在登录 ECR...${NC}"
    aws ecr get-login-password --region $AWS_REGION | \
        docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
}

# 构建和推送 Docker 镜像
build_and_push() {
    echo -e "${GREEN}正在构建 Docker 镜像...${NC}"
    cd backend
    
    docker build -t $ECR_REPOSITORY:latest .
    
    echo -e "${GREEN}正在标记镜像...${NC}"
    docker tag $ECR_REPOSITORY:latest \
        $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest
    
    echo -e "${GREEN}正在推送镜像到 ECR...${NC}"
    docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest
    
    cd ..
    echo -e "${GREEN}镜像推送完成！${NC}"
}

# 部署到 ECS
deploy_to_ecs() {
    echo -e "${GREEN}正在更新 ECS 服务...${NC}"
    
    # 强制新部署
    aws ecs update-service \
        --cluster $ECS_CLUSTER \
        --service $ECS_SERVICE \
        --force-new-deployment \
        --region $AWS_REGION
    
    echo -e "${GREEN}部署已触发！请等待服务稳定...${NC}"
    echo -e "${YELLOW}可以使用以下命令查看部署状态:${NC}"
    echo "aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE --region $AWS_REGION"
}

# 初始化数据库
init_database() {
    echo -e "${GREEN}正在初始化数据库...${NC}"
    echo -e "${YELLOW}这将创建一个临时 ECS 任务来运行数据库初始化脚本。${NC}"
    
    read -p "请输入子网 ID (subnet-xxx): " SUBNET_ID
    read -p "请输入安全组 ID (sg-xxx): " SECURITY_GROUP_ID
    
    aws ecs run-task \
        --cluster $ECS_CLUSTER \
        --task-definition $TASK_DEFINITION \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_ID],securityGroups=[$SECURITY_GROUP_ID],assignPublicIp=ENABLED}" \
        --overrides '{
            "containerOverrides": [{
                "name": "backend",
                "command": ["python", "scripts/init_db.py"]
            }]
        }' \
        --region $AWS_REGION
    
    echo -e "${GREEN}数据库初始化任务已启动！${NC}"
    echo -e "${YELLOW}请查看 ECS 控制台或 CloudWatch 日志以查看执行结果。${NC}"
}

# 显示帮助信息
show_help() {
    echo "AWS 部署辅助脚本"
    echo ""
    echo "使用方法: $0 [command]"
    echo ""
    echo "命令:"
    echo "  setup     - 设置 ECR 仓库并登录"
    echo "  build     - 构建并推送 Docker 镜像"
    echo "  deploy    - 部署到 ECS"
    echo "  init-db   - 初始化数据库"
    echo "  all       - 执行所有步骤（setup + build + deploy）"
    echo ""
    echo "环境变量:"
    echo "  AWS_REGION - AWS 区域（默认: us-east-1）"
    echo ""
    echo "示例:"
    echo "  $0 setup"
    echo "  $0 build"
    echo "  $0 deploy"
    echo "  $0 all"
}

# 主函数
main() {
    check_aws_cli
    check_docker
    
    case "${1:-help}" in
        setup)
            setup_ecr
            ;;
        build)
            setup_ecr
            build_and_push
            ;;
        deploy)
            deploy_to_ecs
            ;;
        init-db)
            init_database
            ;;
        all)
            setup_ecr
            build_and_push
            deploy_to_ecs
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}未知命令: $1${NC}"
            show_help
            exit 1
            ;;
    esac
}

main "$@"

