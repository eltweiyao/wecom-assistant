#!/usr/bin/env python3
"""
测试运行脚本
在没有pytest的环境中也能运行基本测试
"""
import sys
import os
import traceback
from typing import List, Tuple

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_config_tests() -> Tuple[int, int]:
    """运行配置模块测试"""
    passed = 0
    failed = 0
    
    print("=" * 50)
    print("运行配置模块测试")
    print("=" * 50)
    
    try:
        from test_config import TestConfig
        test_class = TestConfig()
        
        # 测试方法列表
        test_methods = [
            'test_config_with_all_required_vars',
            'test_config_missing_required_vars', 
            'test_config_default_values',
            'test_config_custom_values',
            'test_config_summary'
        ]
        
        for method_name in test_methods:
            try:
                print(f"运行 {method_name}...", end=" ")
                method = getattr(test_class, method_name)
                method()
                print("✅ 通过")
                passed += 1
            except Exception as e:
                print(f"❌ 失败: {e}")
                failed += 1
                if "--verbose" in sys.argv:
                    traceback.print_exc()
    
    except Exception as e:
        print(f"❌ 无法运行配置测试: {e}")
        failed += 1
    
    return passed, failed


def run_exception_tests() -> Tuple[int, int]:
    """运行异常处理模块测试"""
    passed = 0
    failed = 0
    
    print("\n" + "=" * 50)
    print("运行异常处理模块测试")
    print("=" * 50)
    
    try:
        from test_exceptions import TestExceptions, TestErrorCodes
        
        # 测试异常处理
        test_exceptions = TestExceptions()
        exception_methods = [
            'test_wecom_assistant_exception_creation',
            'test_specific_exception_types',
            'test_handle_exception_signature_error',
            'test_handle_exception_timeout_error',
            'test_handle_exception_quota_error',
            'test_handle_exception_network_error',
            'test_handle_exception_unknown_error',
            'test_handle_exception_already_wrapped',
            'test_error_reporter'
        ]
        
        for method_name in exception_methods:
            try:
                print(f"运行 {method_name}...", end=" ")
                method = getattr(test_exceptions, method_name)
                method()
                print("✅ 通过")
                passed += 1
            except Exception as e:
                print(f"❌ 失败: {e}")
                failed += 1
                if "--verbose" in sys.argv:
                    traceback.print_exc()
        
        # 测试错误代码
        test_error_codes = TestErrorCodes()
        error_code_methods = [
            'test_error_code_enum',
            'test_error_code_uniqueness'
        ]
        
        for method_name in error_code_methods:
            try:
                print(f"运行 {method_name}...", end=" ")
                method = getattr(test_error_codes, method_name)
                method()
                print("✅ 通过")
                passed += 1
            except Exception as e:
                print(f"❌ 失败: {e}")
                failed += 1
                if "--verbose" in sys.argv:
                    traceback.print_exc()
    
    except Exception as e:
        print(f"❌ 无法运行异常测试: {e}")
        failed += 1
    
    return passed, failed


def run_basic_import_tests() -> Tuple[int, int]:
    """运行基本导入测试"""
    passed = 0
    failed = 0
    
    print("\n" + "=" * 50)
    print("运行基本导入测试")
    print("=" * 50)
    
    modules_to_test = [
        'config',
        'exceptions',
        'logging_config',
        'monitoring',
        'agent',
        'wecom_handler',
        'tools'
    ]
    
    for module_name in modules_to_test:
        try:
            print(f"导入 {module_name}...", end=" ")
            __import__(module_name)
            print("✅ 成功")
            passed += 1
        except Exception as e:
            print(f"❌ 失败: {e}")
            failed += 1
            if "--verbose" in sys.argv:
                traceback.print_exc()
    
    return passed, failed


def test_configuration_validation():
    """测试配置验证功能"""
    print("\n" + "=" * 50)
    print("测试配置验证")
    print("=" * 50)
    
    try:
        from config import config
        summary = config.get_config_summary()
        print("✅ 配置摘要生成成功:")
        for key, value in summary.items():
            print(f"  {key}: {value}")
        return 1, 0
    except Exception as e:
        print(f"❌ 配置验证失败: {e}")
        return 0, 1


def test_logging_system():
    """测试日志系统"""
    print("\n" + "=" * 50)
    print("测试日志系统")
    print("=" * 50)
    
    try:
        from logging_config import logger
        
        # 测试各种日志级别
        logger.info("测试信息日志", test_key="test_value")
        logger.debug("测试调试日志")
        logger.warning("测试警告日志")
        
        # 测试专用日志方法
        logger.log_request_start("test_user", "test_type", "test_request_id")
        logger.log_request_end("test_user", "test_request_id", 1.5, True)
        
        print("✅ 日志系统测试通过")
        return 1, 0
    except Exception as e:
        print(f"❌ 日志系统测试失败: {e}")
        if "--verbose" in sys.argv:
            traceback.print_exc()
        return 0, 1


def test_monitoring_system():
    """测试监控系统"""
    print("\n" + "=" * 50)
    print("测试监控系统")
    print("=" * 50)
    
    try:
        from monitoring import performance_monitor, health_checker, get_performance_report
        
        # 测试性能监控
        performance_monitor.record_metric("test_metric", 100.0)
        performance_monitor.record_request(True, 2.0)
        
        # 测试健康检查
        health_results = health_checker.run_all_checks()
        overall_status = health_checker.get_overall_status()
        
        # 测试性能报告
        report = get_performance_report()
        
        print(f"✅ 监控系统测试通过")
        print(f"  健康状态: {overall_status}")
        print(f"  健康检查数量: {len(health_results)}")
        print(f"  性能报告生成: {'timestamp' in report}")
        
        return 1, 0
    except Exception as e:
        print(f"❌ 监控系统测试失败: {e}")
        if "--verbose" in sys.argv:
            traceback.print_exc()
        return 0, 1


def main():
    """主测试函数"""
    print("🚀 开始运行 wecom-assistant 项目测试")
    print(f"Python 版本: {sys.version}")
    
    total_passed = 0
    total_failed = 0
    
    # 运行各种测试
    test_functions = [
        run_basic_import_tests,
        test_configuration_validation,
        test_logging_system,
        test_monitoring_system,
        run_config_tests,
        run_exception_tests,
    ]
    
    for test_func in test_functions:
        try:
            passed, failed = test_func()
            total_passed += passed
            total_failed += failed
        except Exception as e:
            print(f"❌ 测试函数 {test_func.__name__} 执行失败: {e}")
            total_failed += 1
            if "--verbose" in sys.argv:
                traceback.print_exc()
    
    # 输出总结
    print("\n" + "=" * 50)
    print("测试总结")
    print("=" * 50)
    print(f"✅ 通过: {total_passed}")
    print(f"❌ 失败: {total_failed}")
    print(f"📊 成功率: {total_passed/(total_passed+total_failed)*100:.1f}%" if (total_passed+total_failed) > 0 else "无测试运行")
    
    if total_failed == 0:
        print("\n🎉 所有测试都通过了！")
        return 0
    else:
        print(f"\n⚠️  有 {total_failed} 个测试失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)