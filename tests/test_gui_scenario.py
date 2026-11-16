"""真实 Parkinson 场景 GUI 的离屏集成测试。"""
import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest

import main


@pytest.mark.skipif(not main.PYQT_AVAILABLE, reason='PyQt5 未安装')
def test_real_scenario_tab_loads_structure_and_results():
    app = main.QApplication.instance() or main.QApplication([])
    window = main.MainWindow()
    scenario = window.scenario_tab

    # 全局字号层级。
    for widget in [window, window.page_title, window.page_subtitle, window.nav_buttons[0]]:
        widget.ensurePolished()
    assert window.font().pointSizeF() >= 11.0
    assert window.nav_buttons[0].font().pointSizeF() >= 11.0
    assert window.page_title.font().pointSizeF() >= 20.0
    assert window.page_subtitle.font().pointSizeF() >= 10.0

    assert window.tabs.count() == 8
    assert not window.findChildren(main.QFrame, 'securityPanel')
    assert not any(
        label.text() == 'SECURITY POSTURE'
        for label in window.findChildren(main.QLabel)
    )
    assert isinstance(window.qkd_tab.protocol_animation, main.QKDProtocolAnimation)
    assert not window.qkd_tab.protocol_animation.timer.isActive()
    assert main.QKDProtocolAnimation.TEXT_SIZE_OFFSET == 2
    assert window.qkd_tab.protocol_animation.minimumHeight() >= 122

    # QKD：动画结束后再公布结果。
    qkd = window.qkd_tab
    qkd._on_eve_demo()
    pending_error_rate = qkd.pending_qkd_result['result']['error_rate']
    assert qkd.protocol_animation.timer.isActive()
    assert qkd.qkd_state_card.value_label.text() == '协商中'
    assert qkd.qkd_error_card.value_label.text() == '计算中'
    assert qkd.qkd_send_card.value_label.text() == '等待判定'
    assert not qkd.btn_normal_demo.isEnabled()
    assert not qkd.btn_eve_demo.isEnabled()

    qkd.protocol_animation.timer.stop()
    qkd.protocol_animation.running = False
    qkd.protocol_animation.completed = True
    qkd.protocol_animation.phaseChanged.emit(5)
    qkd.protocol_animation.finished.emit()
    assert qkd.pending_qkd_result is None
    assert qkd.qkd_error_card.value_label.text() == f'{pending_error_rate:.2f}%'
    assert qkd.qkd_state_card.value_label.text() in {'安全', '危险'}
    assert qkd.qkd_send_card.value_label.text() in {'允许发送', '禁止发送'}
    assert qkd.btn_normal_demo.isEnabled()
    assert qkd.btn_eve_demo.isEnabled()
    animated_tabs = [
        (window.privacy_tab, 'privacy'),
        (window.fl_tab, 'federated'),
        (window.attack_tab, 'defense'),
        (window.real_dataset_tab, 'scenario'),
        (window.scenario_tab, 'scenario'),
        (window.spam_scenario_tab, 'scenario'),
        (window.bankruptcy_scenario_tab, 'scenario'),
    ]
    for tab, flow_type in animated_tabs:
        assert isinstance(tab.flow_animation, main.PlainLanguageFlowAnimation)
        assert tab.flow_animation.flow_type == flow_type
        assert not tab.flow_animation.timer.isActive()
        assert main.PlainLanguageFlowAnimation.TEXT_SIZE_OFFSET == 2
        expected_minimum_height = 202 if flow_type == 'privacy' else 192
        assert tab.flow_animation.minimumHeight() >= expected_minimum_height

    window.privacy_tab.play_explainer()
    assert window.privacy_tab.flow_animation.timer.isActive()
    assert window.privacy_tab.flow_animation.running
    window.privacy_tab.flow_animation.reset()

    # 隐私防护：流程结束后再消耗预算并展示数据。
    privacy = window.privacy_tab
    assert privacy.chart_group.title() == '隐私预算决策图'
    assert len(privacy.figure.axes) == 0
    assert privacy.canvas.isHidden()
    assert not privacy.chart_placeholder.isHidden()
    assert privacy.chart_placeholder.text() == '暂无结果'
    visible_privacy_text = [group.title() for group in privacy.findChildren(main.QGroupBox)]
    visible_privacy_text += [label.text() for label in privacy.findChildren(main.QLabel)]
    visible_privacy_text += [button.text() for button in privacy.findChildren(main.QPushButton)]
    assert '实时防护观测' in visible_privacy_text
    assert '▶ 重播加噪过程' not in visible_privacy_text
    assert '看动态数据流：个人痕迹如何在上传前被削弱' not in visible_privacy_text
    assert window.privacy_tab.flow_animation.config['eyebrow'] == ''
    assert all('动画' not in text for text in visible_privacy_text)
    budget_used_before = privacy.qdp.budget.used
    privacy._on_privacy_demo()
    assert privacy.flow_animation.timer.isActive()
    assert privacy.privacy_demo_pending
    assert privacy.qdp.budget.used == budget_used_before
    assert privacy.attack_risk_card.value_label.text() == '分析中'
    assert privacy.noise_card.value_label.text() == '注入中'
    assert privacy.budget_card.value_label.text() == '结算中'
    assert not privacy.btn_noise.isEnabled()
    assert privacy.canvas.isHidden()
    assert privacy.chart_placeholder.text() == '加载中……'
    assert len(privacy.figure.axes) == 0

    privacy.flow_animation.timer.stop()
    privacy.flow_animation.running = False
    privacy.flow_animation.completed = True
    privacy.flow_animation.finished.emit()
    assert not privacy.privacy_demo_pending
    assert privacy.qdp.budget.used > budget_used_before
    assert privacy.attack_risk_card.value_label.text().endswith('%')
    assert privacy.noise_card.value_label.text() not in {'—', '注入中'}
    assert privacy.budget_card.value_label.text() not in {'—', '结算中'}
    assert privacy.btn_noise.isEnabled()
    assert not privacy.canvas.isHidden()
    assert privacy.chart_placeholder.isHidden()
    assert len(privacy.figure.axes) == 1
    privacy_axis = privacy.figure.axes[0]
    privacy_title = privacy_axis.get_title(loc='left')
    assert privacy_title == '风险随隐私预算的变化'
    assert all(text.get_text() != '平衡区间' for text in privacy_axis.texts)
    privacy_legend = privacy_axis.get_legend()
    assert privacy_legend is not None
    assert [text.get_text() for text in privacy_legend.get_texts()] == [
        '信息还原度（代理）', '泄漏风险（估算）', '综合风险'
    ]
    chart_labels = {text.get_text() for text in privacy_axis.texts}
    assert not {'信息还原度', '泄漏风险', '综合风险'} & chart_labels
    assert not any(
        label.startswith(('信息还原 ', '泄漏 ', '综合风险 '))
        for label in chart_labels
    )
    assert not any(label.startswith('ε=') for label in chart_labels)
    assert privacy_axis.get_ylim()[1] <= 65.0
    recoverability_curve = privacy_axis.lines[0].get_ydata()
    leakage_curve = privacy_axis.lines[1].get_ydata()
    combined_curve = privacy_axis.lines[2].get_ydata()
    assert combined_curve == pytest.approx(
        recoverability_curve * leakage_curve / 100.0
    )
    recoverability_before = tuple(privacy_axis.lines[0].get_ydata())
    privacy._compute_tradeoff(update_report=False)
    recoverability_after = tuple(privacy.figure.axes[0].lines[0].get_ydata())
    assert recoverability_after == recoverability_before

    # 拜占庭共识：保留结果区，动画结束后显示投票网络。
    byzantine = window.byzantine_consensus_tab
    assert not byzantine.result_group.isHidden()
    assert byzantine.result_stack.currentWidget() is byzantine.result_placeholder
    assert byzantine.result_placeholder.text() == '暂无结果'
    assert byzantine.node_table.rowCount() == 0
    byzantine._start_consensus_demo()
    assert byzantine.consensus_demo_pending
    assert byzantine.flow_animation.timer.isActive()
    assert byzantine.result_stack.currentWidget() is byzantine.result_placeholder
    assert byzantine.result_placeholder.text() == '加载中……'
    assert not byzantine.btn_run.isEnabled()
    byzantine.flow_animation.timer.stop()
    byzantine.flow_animation.running = False
    byzantine.flow_animation.completed = True
    byzantine.flow_animation.finished.emit()
    assert not byzantine.consensus_demo_pending
    assert byzantine.result_stack.currentWidget() is byzantine.result_content
    assert byzantine.node_table.rowCount() == byzantine.node_spin.value()
    assert byzantine.last_result is not None
    assert byzantine.btn_run.isEnabled()

    # 攻防：先检查防线，再展示结果。
    attack = window.attack_tab
    visible_attack_text = [group.title() for group in attack.findChildren(main.QGroupBox)]
    visible_attack_text += [label.text() for label in attack.findChildren(main.QLabel)]
    visible_attack_text += [button.text() for button in attack.findChildren(main.QPushButton)]
    assert '实时攻防观测' in visible_attack_text
    assert '▶ 预览四层防线' not in visible_attack_text
    assert all('动画' not in text for text in visible_attack_text)
    assert attack.flow_animation.config['eyebrow'] == ''
    attack._on_attack('poisoning')
    assert attack.pending_attack_type == 'poisoning'
    assert attack.flow_animation.timer.isActive()
    assert attack.flow_animation.steps[1][0] == '拜占庭共识 + 鲁棒聚合'
    assert attack.simulator.attack_history == []
    assert attack.attack_poison_card.value_label.text() == '检测中'
    assert not attack.btn_all.isEnabled()
    attack.flow_animation.timer.stop()
    attack.flow_animation.running = False
    attack.flow_animation.completed = True
    attack.flow_animation.finished.emit()
    assert attack.pending_attack_type is None
    assert len(attack.simulator.attack_history) == 1
    assert attack.attack_poison_card.value_label.text().startswith('降低')
    assert attack.btn_all.isEnabled()

    # 联邦训练参数固定，恶意节点可手动注入。
    federated = window.fl_tab
    assert (
        federated.training_parameters_group.sizePolicy().verticalPolicy()
        == main.QSizePolicy.Maximum
    )
    federated.training_parameters_group.setChecked(True)
    assert federated.btn_train.text() == '开始标准联邦学习'
    assert federated.btn_multi.text() == '恶意节点注入'
    assert federated.btn_kfold.text() == '运行5折验证'
    assert not federated.client_slider.isEnabled()
    assert not federated.lr_slider.isEnabled()
    assert not federated.bond_slider.isEnabled()
    assert federated.mal_combo.isEnabled()
    assert [
        federated.mal_combo.itemData(index)
        for index in range(federated.mal_combo.count())
    ] == [0, 1, 2]
    assert federated.table.rowCount() == 1
    assert federated.table.item(0, 0).text() == '暂无结果'
    assert federated.fl_accuracy_card.value_label.text() == '待开始'
    assert federated.fl_security_card.value_label.text() == '待开始'
    assert federated.fl_cv_card.value_label.text() == '待开始'
    assert federated.fl_mal_card.value_label.text() == '待开始'
    assert federated.flow_animation.config['eyebrow'] == ''
    assert not federated.result_workspace.isHidden()
    assert not hasattr(federated, 'result_guide')
    assert federated.chart_stack.currentWidget() is federated.chart_placeholder
    assert '暂无结果' in federated.chart_placeholder.text()

    # 展示入口不依赖现场训练。
    federated._run_single_round = lambda: (_ for _ in ()).throw(
        AssertionError('不应执行现场训练')
    )
    federated._on_demo_train()
    assert federated.federated_demo_pending == 'training'
    assert federated.flow_animation.timer.isActive()
    assert federated.fl_accuracy_card.value_label.text() == '训练中'
    assert federated.fl_security_card.value_label.text() == '压缩中'
    assert federated.table.columnCount() == 2
    assert not federated.result_workspace.isHidden()
    assert federated.chart_stack.currentWidget() is federated.chart_placeholder
    assert '训练进行中' in federated.chart_placeholder.text()
    assert not federated.btn_train.isEnabled()

    federated.flow_animation.timer.stop()
    federated.flow_animation.running = False
    federated.flow_animation.completed = True
    federated.flow_animation.finished.emit()
    assert federated.federated_demo_pending is None
    assert federated.table.rowCount() == 20
    assert federated.fl_accuracy_card.value_label.text() == '91.53%'
    assert federated.fl_security_card.value_label.text() == '23.54%'
    assert federated.fl_cv_card.value_label.text() == '90.27% ± 1.93%'
    assert federated.fl_mal_card.value_label.text() == '94.58%'
    assert not federated.result_workspace.isHidden()
    assert federated.chart_stack.currentWidget() is federated.canvas
    assert federated.btn_train.isEnabled()
    benchmark = federated._read_precomputed_results()['federated_learning']
    baseline_result = benchmark['baseline_fedavg']
    secure_result = benchmark['secure_qdp_adaptive_mpo']
    assert secure_result['final_accuracy'] > baseline_result['final_accuracy']
    assert secure_result['final_loss'] < baseline_result['final_loss']
    assert secure_result['final_accuracy_std'] < baseline_result['final_accuracy_std']
    assert secure_result['aggregation_method'] == baseline_result['aggregation_method'] == 'fedavg'
    assert secure_result['avg_communication_saving_pct'] >= 20.0
    assert secure_result['learning_rate_schedule'] == 'constant'
    assert secure_result['learning_rate_start'] == 0.7
    assert secure_result['learning_rate_end'] == 0.7
    assert secure_result['qdp_noise_seed'] == 'varied_by_run'
    assert secure_result['qdp_clip_norm'] == 1.0
    assert secure_result['mpo_max_reconstruction_error'] == 0.0015
    assert secure_result['compression_error_feedback'] is True
    assert secure_result['n_runs'] == baseline_result['n_runs'] == 5
    accuracy_axis, loss_axis = federated.figure.axes
    assert accuracy_axis.get_position().width > 0.30
    assert loss_axis.get_position().width > 0.30
    assert '测试准确率' in accuracy_axis.get_title()
    assert '测试损失' in loss_axis.get_title()
    assert any(
        '误差反馈' in text.get_text()
        for text in accuracy_axis.get_legend().get_texts()
    )
    federated._on_poison_demo()
    assert federated.federated_demo_pending == 'poisoning'
    assert not federated.result_workspace.isHidden()
    assert federated.chart_stack.currentWidget() is federated.chart_placeholder
    assert '对照实验进行中' in federated.chart_placeholder.text()
    assert federated.pending_malicious_count == 1
    assert not federated.mal_combo.isEnabled()
    assert federated.fl_mal_card.value_label.text() == '分析中'
    federated.flow_animation.timer.stop()
    federated.flow_animation.running = False
    federated.flow_animation.completed = True
    federated.flow_animation.finished.emit()
    assert federated.table.rowCount() == 3
    assert federated.table.item(1, 0).text() == 'Median'
    assert federated.fl_accuracy_card.value_label.text() == '91.53%'
    assert federated.fl_security_card.value_label.text() == '23.54%'
    assert federated.fl_cv_card.value_label.text() == '90.27% ± 1.93%'
    assert federated.fl_mal_card.value_label.text() == '92.95%'
    assert federated.table.item(1, 1).text() == '0.3091'
    assert federated.fl_chain_card.value_label.text() == '实验完成'
    assert not federated.result_workspace.isHidden()
    assert federated.chart_stack.currentWidget() is federated.canvas
    assert federated.chart_group.title() == '恶意节点注入 · 防御验证结果'
    figure_text = [
        text.get_text()
        for axis in federated.figure.axes
        for text in axis.texts
    ]
    assert any('恶意更新进入' in text for text in figure_text)
    assert '注入数量: 1/5' in federated.log_output.toPlainText()
    assert federated.mal_combo.isEnabled()
    assert len(federated.figure.axes) == 3

    federated._on_kfold_demo()
    assert federated.federated_demo_pending == 'kfold'
    assert not federated.result_workspace.isHidden()
    assert federated.chart_stack.currentWidget() is federated.chart_placeholder
    assert '5折验证进行中' in federated.chart_placeholder.text()
    assert federated.fl_cv_card.value_label.text() == '验证中'
    federated.flow_animation.timer.stop()
    federated.flow_animation.running = False
    federated.flow_animation.completed = True
    federated.flow_animation.finished.emit()
    assert federated.table.rowCount() == 5
    assert federated.fl_accuracy_card.value_label.text() == '91.53%'
    assert federated.fl_security_card.value_label.text() == '23.54%'
    assert federated.fl_cv_card.value_label.text() == '90.27% ± 1.93%'
    assert federated.fl_mal_card.value_label.text() == '94.58%'
    assert federated.fl_chain_card.value_label.text() == '验证完成'
    assert not federated.result_workspace.isHidden()
    assert federated.chart_stack.currentWidget() is federated.canvas
    assert '5折交叉验证演示完成' in federated.log_output.toPlainText()
    window.qkd_tab.advanced_group.setChecked(True)
    app.processEvents()
    assert window.qkd_tab.eve_combo.height() >= 36
    assert window.qkd_tab.enc_combo.height() >= 36
    assert not hasattr(window.qkd_tab, 'btn_distribute')
    assert not hasattr(window.qkd_tab, 'msg_input')
    assert not hasattr(window.qkd_tab, 'btn_send')
    assert all(
        button.text() not in {'手动执行量子密钥分发', '发送加密消息'}
        for button in window.qkd_tab.findChildren(main.QPushButton)
    )
    window.qkd_tab.advanced_group.setChecked(False)
    app.processEvents()
    assert window.tabs.tabText(3) == '◉ 拜占庭共识'
    assert window.tabs.tabText(4) == '⛓ 区块链篡改'
    assert window.tabs.tabText(5) == '攻防'
    assert window.tabs.tabText(6) == '▦ 真实场景验证'
    assert window.tabs.tabText(7) == '⊕ 用户接口'
    integrated = window.real_dataset_tab
    assert not hasattr(integrated, 'dataset_tabs')
    visible_dataset_text = [
        label.text() for label in integrated.findChildren(main.QLabel)
    ]
    assert '医疗 · Parkinson 语音' in visible_dataset_text
    assert '邮件 · 垃圾邮件识别' in visible_dataset_text
    assert '金融 · 企业破产预警' in visible_dataset_text
    assert integrated.run_button.text() == '开始三类数据联合验证'
    assert integrated.results_stack.currentWidget() is integrated.results_placeholder
    assert integrated.results_placeholder.text() == '暂无结果'
    assert integrated.result_table.rowCount() == 0
    visible_dataset_flows = [
        flow for flow in integrated.findChildren(main.PlainLanguageFlowAnimation)
        if not integrated._compatibility_holder.isAncestorOf(flow)
    ]
    assert visible_dataset_flows == [integrated.flow_animation]
    assert integrated._compatibility_holder.isHidden()
    assert [button.text() for button in window.nav_buttons][-2:] == [
        '真实场景验证', '用户接口',
    ]
    assert [
        label.text() for label in window.findChildren(main.QLabel, 'navSection')
    ][-2:] == ['场景验证', '可用接口']
    custom_interface = window.custom_dataset_tab
    assert custom_interface.dataset_name.text() == '我的联邦数据集'
    assert custom_interface.client_count.value() == 5
    assert custom_interface.round_count.value() == 20
    assert custom_interface.schema_table.rowCount() == 4
    assert len(custom_interface.security_checks) == 5
    assert all(check.isChecked() for check in custom_interface.security_checks)
    create_buttons = [
        button for button in custom_interface.findChildren(main.QPushButton)
        if '创建接入任务' in button.text()
    ]
    assert len(create_buttons) == 1
    assert create_buttons[0].text() == '创建接入任务'
    assert create_buttons[0].isEnabled()
    assert not any(
        '原型' in label.text() for label in custom_interface.findChildren(main.QLabel)
    )
    custom_interface.data_location.setText('/tmp/example.csv')
    custom_interface.target_field.setText('label')
    custom_interface.client_field.setText('client_id')
    create_buttons[0].click()
    assert custom_interface.interface_state.text() == '接入任务已创建'
    assert all(
        button.text() not in {'医疗场景', '邮件场景', '金融场景'}
        for button in window.nav_buttons
    )
    assert all(
        '重新读取结果' not in button.text()
        for button in window.findChildren(main.QPushButton)
    )

    # 三个数据集共用一次动画和结果加载。
    integrated._start_experiment()
    assert integrated.scenario_demo_pending
    assert integrated.process is None
    assert integrated.flow_animation.timer.isActive()
    assert integrated.results_stack.currentWidget() is integrated.results_placeholder
    assert integrated.results_placeholder.text() == '加载中……'
    assert not integrated.run_button.isEnabled()
    integrated.flow_animation.timer.stop()
    integrated.flow_animation.running = False
    integrated.flow_animation.completed = True
    integrated.flow_animation.finished.emit()
    assert not integrated.scenario_demo_pending
    assert integrated.results_stack.currentWidget() is integrated.results_content
    assert integrated.result_table.rowCount() == 3
    expected_scenario_metrics = [
        ('43.16%', '65.74%', '+22.58 pp'),
        ('20.25%', '86.24%', '+65.99 pp'),
        ('26.99%', '83.70%', '+56.71 pp'),
    ]
    for row, expected_values in enumerate(expected_scenario_metrics):
        assert tuple(
            integrated.result_table.item(row, column).text()
            for column in (3, 4, 5)
        ) == expected_values
    assert len(integrated.figure.axes) == 2
    assert integrated.run_button.isEnabled()
    assert all(
        label.text().startswith('已完成')
        for label in integrated.dataset_status_labels.values()
    )

    for scene_tab in [
        window.scenario_tab,
        window.spam_scenario_tab,
        window.bankruptcy_scenario_tab,
    ]:
        workspace = scene_tab.findChild(main.QTabWidget, 'sceneTabs')
        assert workspace is not None
        assert workspace.count() == 2
        assert [workspace.tabText(i) for i in range(2)] == [
            '场景概览', '实验结果'
        ]
        assert scene_tab.run_button.text() == '开始20轮安全联合训练'
        assert scene_tab.flow_animation.config['eyebrow'] == ''
        assert scene_tab.result_table.rowCount() == 0
        assert not scene_tab.scenario_demo_pending
        visible_scene_text = [group.title() for group in scene_tab.findChildren(main.QGroupBox)]
        visible_scene_text += [label.text() for label in scene_tab.findChildren(main.QLabel)]
        visible_scene_text += [button.text() for button in scene_tab.findChildren(main.QPushButton)]
        assert '实时训练观测' in visible_scene_text
        assert '▶ 看懂一次联合训练' not in visible_scene_text
        assert all('动画' not in text for text in visible_scene_text)
    assert len(scenario.client_cards) == 5
    assert scenario.dataset_card.value_label.text() == '待开始'
    assert window.spam_scenario_tab.size_card.value_label.text() == '待开始'
    assert window.bankruptcy_scenario_tab.size_card.value_label.text() == '待开始'

    # 场景页只加载预计算结果。
    for scene_tab in [
        window.scenario_tab,
        window.spam_scenario_tab,
        window.bankruptcy_scenario_tab,
    ]:
        scene_tab._start_experiment()
        assert scene_tab.scenario_demo_pending
        assert scene_tab.process is None
        assert scene_tab.flow_animation.timer.isActive()
        assert scene_tab.result_table.rowCount() == 0
        assert not scene_tab.run_button.isEnabled()
        if isinstance(scene_tab, main.ParkinsonScenarioTab):
            assert all(
                card.detail_label.text() == '处理中……'
                for card in scene_tab.client_cards
            )
        scene_tab.flow_animation.timer.stop()
        scene_tab.flow_animation.running = False
        scene_tab.flow_animation.completed = True
        scene_tab.flow_animation.finished.emit()
        assert not scene_tab.scenario_demo_pending
        assert scene_tab.result_table.rowCount() == 2
        assert scene_tab.run_button.isEnabled()
        assert scene_tab.run_state.text() == ''
        assert len(scene_tab.figure.axes) == 3
        summary_axis, metric_axis, seed_axis = scene_tab.figure.axes
        assert any(
            '逐种子胜出' in text.get_text()
            for text in summary_axis.texts
        )
        assert '核心指标恢复' in metric_axis.get_title(loc='left')
        assert '五种子配对复核' in seed_axis.get_title(loc='left')
        # 独立种子不能连成时间序列。
        assert all(len(line.get_xdata()) <= 2 for line in seed_axis.lines)
        assert scene_tab.result_table.maximumHeight() <= 112

    assert scenario.dataset_card.value_label.text() == '756条 / 252人'
    assert scenario.split_card.value_label.text() == '泄漏 0'
    assert scenario.compress_card.value_label.text() == '42.63%'
    assert scenario.result_table.item(0, 0).text() == '投毒FedAvg'
    assert scenario.result_table.item(1, 0).text() == '四层安全方案'
    assert scenario.result_table.item(1, 1).text() == '73.20%'
    assert scenario.result_table.item(1, 2).text() == '61.77%'

    assert window.spam_scenario_tab.size_card.value_label.text() == '4,601条'
    assert window.spam_scenario_tab.compress_card.value_label.text() == '39.27%'
    assert window.spam_scenario_tab.result_table.rowCount() == 2
    assert window.spam_scenario_tab.result_table.item(0, 0).text() == '投毒FedAvg'
    assert window.spam_scenario_tab.result_table.item(1, 0).text() == '四层安全方案'
    assert window.bankruptcy_scenario_tab.size_card.value_label.text() == '6,819条'
    assert window.bankruptcy_scenario_tab.compress_card.value_label.text() == '38.81%'
    assert window.bankruptcy_scenario_tab.result_table.rowCount() == 2
    assert window.bankruptcy_scenario_tab.result_table.item(0, 0).text() == '投毒FedAvg'
    assert window.bankruptcy_scenario_tab.result_table.item(1, 0).text() == '四层安全方案'

    window.close()
    app.processEvents()


@pytest.mark.skipif(not main.PYQT_AVAILABLE, reason='PyQt5 未安装')
def test_all_demo_branches_clear_running_states_after_completion():
    app = main.QApplication.instance() or main.QApplication([])
    running_values = {
        '协商中', '计算中', '等待判定', '分析中', '注入中', '结算中',
        '训练中', '压缩中', '验证中', '等待完成', '检测中', '运行中',
        '准备中', '校验中',
    }

    def finish_flow(flow):
        flow.timer.stop()
        flow.running = False
        flow.completed = True
        flow.finished.emit()

    def assert_cards_complete(cards):
        values = [card.value_label.text() for card in cards]
        assert not running_values.intersection(values), values

    qkd = main.QKDTab()
    qkd_cards = [qkd.qkd_state_card, qkd.qkd_error_card, qkd.qkd_send_card]
    for action in [qkd._on_normal_demo, qkd._on_eve_demo]:
        action()
        qkd.protocol_animation.timer.stop()
        qkd.protocol_animation.running = False
        qkd.protocol_animation.completed = True
        qkd.protocol_animation.finished.emit()
        assert_cards_complete(qkd_cards)

    privacy = main.PrivacyTab()
    privacy_cards = [
        privacy.privacy_mode_card, privacy.attack_risk_card,
        privacy.noise_card, privacy.budget_card,
    ]
    for mode in ['strong', 'balanced', 'accurate']:
        privacy._set_privacy_preset(mode)
        assert privacy.canvas.isHidden()
        privacy._on_privacy_demo()
        assert privacy.chart_placeholder.text() == '加载中……'
        finish_flow(privacy.flow_animation)
        assert not privacy.canvas.isHidden()
        assert privacy.chart_placeholder.isHidden()
        assert_cards_complete(privacy_cards)

    federated = main.FederatedTab()
    federated_cards = [
        federated.fl_accuracy_card, federated.fl_security_card,
        federated.fl_cv_card, federated.fl_mal_card, federated.fl_chain_card,
    ]
    for mode in ['training', 'poisoning', 'kfold']:
        federated._start_federated_demo(mode)
        finish_flow(federated.flow_animation)
        assert_cards_complete(federated_cards)

    attack = main.AttackTab()
    attack_cards = [
        attack.attack_detect_card, attack.attack_poison_card,
        attack.attack_privacy_card, attack.attack_chain_card,
    ]
    for mode in ['eavesdropping', 'poisoning', 'leakage', 'tampering', 'all']:
        attack._start_attack_demo(mode)
        finish_flow(attack.flow_animation)
        assert_cards_complete(attack_cards)

    scenarios = [
        (
            main.ParkinsonScenarioTab(),
            lambda tab: [
                tab.dataset_card, tab.split_card, tab.robust_card,
                tab.compress_card, tab.repeat_card,
            ],
        ),
        (
            main.MultiDomainScenarioTab('spam'),
            lambda tab: [
                tab.size_card, tab.feature_card, tab.attack_card,
                tab.repeat_card, tab.compress_card,
            ],
        ),
        (
            main.MultiDomainScenarioTab('bankruptcy'),
            lambda tab: [
                tab.size_card, tab.feature_card, tab.attack_card,
                tab.repeat_card, tab.compress_card,
            ],
        ),
    ]
    for scenario, cards_for in scenarios:
        scenario._start_experiment()
        finish_flow(scenario.flow_animation)
        assert_cards_complete(cards_for(scenario))
        assert all(
            '训练中' not in card.detail_label.text()
            for card in scenario.client_cards
        )

    app.processEvents()


def test_gradient_leakage_defense_is_stable_and_stronger():
    first = main.AttackSimulator(seed=2024).gradient_leakage_attack()
    second = main.AttackSimulator(seed=2024).gradient_leakage_attack()
    assert first['epsilon_scan'] == second['epsilon_scan']

    tab = main.AttackTab()
    protection_score = tab._attack_protection_scores([first])[2] * 100
    assert 90.0 <= protection_score <= 100.0
    assert first['defense_config'].startswith('L2 范数裁剪 C=0.3')


def test_byzantine_consensus_module_shows_tolerance_boundary():
    app = main.QApplication.instance() or main.QApplication([])
    tab = main.ByzantineConsensusTab()

    assert tab.node_spin.value() == 7
    assert tab.malicious_spin.value() == 2
    assert tab.tolerance_card.value_label.text() == 't = 2'
    assert all(
        button.text() != '恢复默认场景'
        for button in tab.findChildren(main.QPushButton)
    )
    assert tab.node_spin.buttonSymbols() == main.QSpinBox.NoButtons
    assert tab.malicious_spin.buttonSymbols() == main.QSpinBox.NoButtons
    assert tab.qubit_spin.buttonSymbols() == main.QSpinBox.NoButtons
    assert not hasattr(tab, 'proposal_combo')
    assert tab.CONSENSUS_VALUE == 'current-federated-model-update'

    within_tolerance = tab._run_consensus()
    assert within_tolerance['malicious_nodes'] == [5, 6]
    assert within_tolerance['detected_malicious'] == [5, 6]
    assert within_tolerance['consensus_reached'] is True
    assert within_tolerance['detection_accuracy'] == pytest.approx(1.0)
    assert tab.node_table.rowCount() == 7
    assert tab.consensus_card.value_label.text() == '已达成'
    assert tab.node_table.item(5, 1).text() == '恶意'
    assert tab.node_table.item(5, 3).text() == '已筛除'

    tab.malicious_spin.setValue(3)
    beyond_tolerance = tab._run_consensus()
    assert beyond_tolerance['malicious_nodes'] == [4, 5, 6]
    assert beyond_tolerance['detected_malicious'] == [4, 5, 6]
    assert beyond_tolerance['consensus_reached'] is False
    assert tab.consensus_card.value_label.text() == '已拒绝'
    assert '不写入账本' in tab.consensus_card.detail_label.text()
    assert '已超出容错范围' in tab.boundary_note.text()

    tab._reset_demo()
    assert tab.node_spin.value() == 7
    assert tab.malicious_spin.value() == 2
    assert tab.last_result is None
    assert tab.node_table.rowCount() == 0
    app.processEvents()


def test_blockchain_tamper_module_uses_real_chain_validation():
    app = main.QApplication.instance() or main.QApplication([])
    tab = main.BlockchainTamperTab()

    assert tab.blockchain.validate_chain() == (True, '区块链完整有效')
    assert tab.block_combo.count() == 5
    assert tab.tamper_value_spin.value() == pytest.approx(99.9)
    assert tab.tamper_value_spin.maximum() == pytest.approx(100.0)
    assert all(
        button.text() != '恢复原始链'
        for button in tab.findChildren(main.QPushButton)
    )
    assert tab.ATTACK_MODES == {'edit_only': '直接修改区块数据'}
    assert not hasattr(tab, 'mode_combo')

    target_index = tab.block_combo.findData(3)
    tab.block_combo.setCurrentIndex(target_index)

    tab._execute_tamper()
    direct_result = tab._validate_chain()
    assert direct_result['detected'] is True
    assert '区块 3 PoW 验证失败' == direct_result['message']

    tab._restore_chain()
    assert tab.blockchain.validate_chain() == (True, '区块链完整有效')
    assert tab.last_attack is None
    assert tab.btn_validate.isEnabled() is False
    app.processEvents()


def test_new_security_modules_reveal_data_only_after_process_finishes():
    app = main.QApplication.instance() or main.QApplication([])

    consensus = main.ByzantineConsensusTab()
    consensus.btn_run.click()
    assert consensus.consensus_demo_pending is True
    assert consensus.flow_animation.timer.isActive()
    assert consensus.last_result is None
    assert consensus.node_table.rowCount() == 0
    assert not consensus.result_group.isHidden()
    assert consensus.result_stack.currentWidget() is consensus.result_placeholder
    assert consensus.result_placeholder.text() == '加载中……'
    assert not consensus.btn_run.isEnabled()

    consensus.flow_animation.timer.stop()
    consensus.flow_animation.running = False
    consensus.flow_animation.completed = True
    consensus.flow_animation.finished.emit()
    assert consensus.consensus_demo_pending is False
    assert consensus.last_result is not None
    assert consensus.node_table.rowCount() == 7
    assert not consensus.result_group.isHidden()
    assert consensus.result_stack.currentWidget() is consensus.result_content
    assert consensus.btn_run.isEnabled()

    ledger = main.BlockchainTamperTab()
    assert ledger.validation_flow_animation.steps == ledger.VALIDATION_FLOW_STEPS
    assert ledger.validation_flow_animation.final_caption == '暂无校验结果'
    assert not ledger.tamper_result_group.isHidden()
    assert not ledger.validation_result_group.isHidden()
    assert ledger.tamper_result_stack.currentWidget() is ledger.tamper_result_placeholder
    assert ledger.validation_result_stack.currentWidget() is ledger.validation_result_placeholder
    assert ledger.tamper_result_placeholder.text() == '暂无结果'
    assert ledger.validation_result_placeholder.text() == '暂无结果'
    ledger.btn_tamper.click()
    assert ledger.pending_ledger_action == 'tamper'
    assert ledger.tamper_flow_animation.timer.isActive()
    assert not ledger.validation_flow_animation.timer.isActive()
    assert ledger.last_attack is None
    assert not ledger.tamper_result_group.isHidden()
    assert not ledger.validation_result_group.isHidden()
    assert ledger.tamper_result_stack.currentWidget() is ledger.tamper_result_placeholder
    assert ledger.tamper_result_placeholder.text() == '加载中……'
    assert ledger.validation_result_stack.currentWidget() is ledger.validation_result_placeholder
    assert not ledger.btn_tamper.isEnabled()

    ledger.tamper_flow_animation.timer.stop()
    ledger.tamper_flow_animation.running = False
    ledger.tamper_flow_animation.completed = True
    ledger.tamper_flow_animation.finished.emit()
    assert ledger.pending_ledger_action is None
    assert ledger.last_attack is not None
    assert ledger.tamper_flow_animation.completed
    assert ledger.tamper_chain_view.validation_state == 'tampered'
    assert not ledger.tamper_result_group.isHidden()
    assert ledger.tamper_result_stack.currentWidget() is ledger.tamper_result_content
    assert not ledger.validation_result_group.isHidden()
    assert ledger.validation_result_stack.currentWidget() is ledger.validation_result_placeholder
    assert ledger.btn_validate.isEnabled()

    ledger.btn_validate.click()
    assert ledger.pending_ledger_action == 'validate'
    assert ledger.validation_flow_animation.timer.isActive()
    assert ledger.tamper_flow_animation.completed
    assert ledger.last_validation is None
    assert not ledger.tamper_result_group.isHidden()
    assert ledger.tamper_result_stack.currentWidget() is ledger.tamper_result_content
    assert not ledger.validation_result_group.isHidden()
    assert ledger.validation_result_stack.currentWidget() is ledger.validation_result_placeholder
    assert ledger.validation_result_placeholder.text() == '加载中……'

    ledger.validation_flow_animation.timer.stop()
    ledger.validation_flow_animation.running = False
    ledger.validation_flow_animation.completed = True
    ledger.validation_flow_animation.finished.emit()
    assert ledger.pending_ledger_action is None
    assert ledger.last_validation is not None
    assert ledger.tamper_flow_animation.completed
    assert ledger.validation_flow_animation.completed
    assert ledger.tamper_chain_view.validation_state == 'tampered'
    assert ledger.validation_chain_view.validation_state == 'detected'
    assert not ledger.tamper_result_group.isHidden()
    assert not ledger.validation_result_group.isHidden()
    assert ledger.tamper_result_stack.currentWidget() is ledger.tamper_result_content
    assert ledger.validation_result_stack.currentWidget() is ledger.validation_result_content
    assert not ledger.btn_validate.isEnabled()
    app.processEvents()


def test_manual_malicious_node_control_changes_poisoning_result():
    app = main.QApplication.instance() or main.QApplication([])
    tab = main.FederatedTab()
    tab.training_parameters_group.setChecked(True)

    one_node = tab._calculate_poisoning_result(5, 1)
    two_nodes = tab._calculate_poisoning_result(5, 2)
    assert one_node['within_tolerance'] is True
    assert two_nodes['within_tolerance'] is False
    assert two_nodes['aggregation_delta_norms']['fedavg'] > one_node['aggregation_delta_norms']['fedavg']
    assert two_nodes['aggregation_delta_norms'] == {
        'fedavg': 8.8456, 'median': 0.4797, 'krum': 0.4454
    }

    two_node_index = tab.mal_combo.findData(2)
    assert two_node_index >= 0
    tab.mal_combo.setCurrentIndex(two_node_index)
    assert '注入2个' in tab.btn_train.text()
    assert '超出容错' in tab.mal_combo.currentText()
    assert not hasattr(tab, 'source_note')

    # 主入口和快捷入口必须使用同一参数。
    tab._on_demo_train()
    assert tab.federated_demo_pending == 'poisoning'
    assert tab.pending_malicious_count == 2
    assert not tab.mal_combo.isEnabled()
    tab.flow_animation.timer.stop()
    tab.flow_animation.running = False
    tab.flow_animation.completed = True
    tab.flow_animation.finished.emit()

    assert tab.fl_mal_card.value_label.text() == '94.58%'
    assert tab.table.item(1, 1).text() == '0.4797'
    assert '超出共识容错范围' in tab.fl_chain_card.detail_label.text()
    assert '注入数量: 2/5' in tab.log_output.toPlainText()
    assert tab.mal_combo.isEnabled()

    tab._on_reset()
    assert tab.mal_combo.currentData() == 0
    assert tab.btn_train.text() == '开始标准联邦学习'
    assert not tab.result_workspace.isHidden()
    assert tab.table.item(0, 0).text() == '暂无结果'
    assert tab.chart_stack.currentWidget() is tab.chart_placeholder
    assert '暂无结果' in tab.chart_placeholder.text()
    app.processEvents()


def test_attack_result_reveal_is_staggered():
    app = main.QApplication.instance() or main.QApplication([])
    early_progress = [
        main.AttackTab._staggered_attack_bar_progress(0.30, index)
        for index in range(4)
    ]
    assert early_progress[0] > early_progress[1] > early_progress[2] > early_progress[3]
    assert all(
        main.AttackTab._staggered_attack_bar_progress(1.0, index) == 1.0
        for index in range(4)
    )

    tab = main.AttackTab()
    tab.simulator.attack_history = [
        {'attack_type': 'eavesdropping', 'detection_success': True},
        {'attack_type': 'model_poisoning', 'robust_reduction_rate': 0.95},
        {
            'attack_type': 'gradient_leakage',
            'epsilon_scan': [{'protection_success_rate': 0.93}],
        },
        {'attack_type': 'blockchain_tampering', 'detection_success': True},
    ]
    tab._start_attack_result_reveal()
    assert tab.result_reveal_timer.isActive()
    assert tab.result_reveal_frame == 0
    tab._stop_attack_result_reveal()
    assert not tab.result_reveal_timer.isActive()
    app.processEvents()


def test_individual_attack_results_accumulate_without_duplicates():
    app = main.QApplication.instance() or main.QApplication([])
    tab = main.AttackTab()

    def finish_attack():
        tab.flow_animation.timer.stop()
        tab.flow_animation.running = False
        tab.flow_animation.completed = True
        tab.flow_animation.finished.emit()

    tab._start_attack_demo('eavesdropping')
    finish_attack()
    assert [
        result['attack_type'] for result in tab.simulator.attack_history
    ] == ['eavesdropping']
    eavesdropping_card_value = tab.attack_detect_card.value_label.text()

    tab._start_attack_demo('tampering')
    assert tab.attack_detect_card.value_label.text() == eavesdropping_card_value
    finish_attack()
    assert [
        result['attack_type'] for result in tab.simulator.attack_history
    ] == ['eavesdropping', 'blockchain_tampering']
    assert sum(
        text.get_text() == '待验证'
        for text in tab.figure.axes[0].texts
    ) == 2

    # 重跑只刷新当前场景。
    tab._start_attack_demo('eavesdropping')
    finish_attack()
    attack_types = [
        result['attack_type'] for result in tab.simulator.attack_history
    ]
    assert attack_types == ['eavesdropping', 'blockchain_tampering']
    assert len(attack_types) == len(set(attack_types))
    app.processEvents()


def test_all_process_animations_use_easing_and_completion_settle():
    app = main.QApplication.instance() or main.QApplication([])

    qkd = main.QKDProtocolAnimation()
    qkd.resize(1180, 245)
    qkd.start(eve_active=True, error_rate=23.5)
    qkd.timer.stop()
    assert qkd._qber_bar_style()[0] == '加载中'
    animation_seconds = (
        qkd.FRAME_INTERVAL_MS / 1000.0 / qkd.PROGRESS_PER_FRAME
    )
    assert animation_seconds >= 15.0
    qkd.progress = 0.55
    assert not qkd.grab().isNull()
    qkd.progress = 1.0
    qkd_finished = []
    qkd.finished.connect(lambda: qkd_finished.append(True))
    for _ in range(qkd.SETTLE_FRAMES - 1):
        qkd._advance()
    assert qkd.running
    assert not qkd.completed
    assert not qkd_finished
    qkd._advance()
    assert qkd.completed
    assert qkd_finished == [True]
    assert qkd._qber_bar_style()[0] == '风险'
    qkd.error_rate = 3.0
    assert qkd._qber_bar_style()[0] == '安全'
    assert not qkd.grab().isNull()

    for flow_type in ['privacy', 'federated', 'defense', 'scenario']:
        flow = main.PlainLanguageFlowAnimation(flow_type)
        flow_seconds = (
            flow.FRAME_INTERVAL_MS / 1000.0 / flow.PROGRESS_PER_FRAME
        )
        assert flow_seconds >= 8.0
        flow.resize(1180, 214 if flow_type == 'privacy' else 204)
        flow.play(attack_type='leakage' if flow_type == 'defense' else '')
        flow.timer.stop()
        flow.progress = 0.55
        assert 0.0 <= flow._stage_progress(flow._active_index()) <= 1.0
        assert not flow.grab().isNull()
        flow.reset()

    # 窄屏上传阶段。
    upload_flow = main.PlainLanguageFlowAnimation('federated')
    upload_flow.resize(760, 204)
    upload_flow.play()
    upload_flow.timer.stop()
    upload_flow.progress = 0.31
    assert upload_flow._active_index() == 1
    assert not upload_flow.grab().isNull()
    upload_flow.reset()

    # 窄屏安全聚合阶段。
    federated_flow = main.PlainLanguageFlowAnimation('federated')
    federated_flow.resize(760, 204)
    federated_flow.play()
    federated_flow.timer.stop()
    federated_flow.progress = 0.72
    assert federated_flow._active_index() == 3
    assert not federated_flow.grab().isNull()
    federated_flow.reset()

    # 窄屏模型下发阶段。
    scenario_flow = main.PlainLanguageFlowAnimation('scenario')
    scenario_flow.resize(760, 204)
    scenario_flow.play()
    scenario_flow.timer.stop()
    scenario_flow.progress = 0.92
    assert scenario_flow._active_index() == 4
    assert not scenario_flow.grab().isNull()
    scenario_flow.reset()

    flow = main.PlainLanguageFlowAnimation('federated')
    flow.play()
    flow.timer.stop()
    flow.progress = 1.0
    flow_finished = []
    flow.finished.connect(lambda: flow_finished.append(True))
    for _ in range(flow.SETTLE_FRAMES - 1):
        flow._advance()
    assert flow.running
    assert not flow.completed
    assert not flow_finished
    flow._advance()
    assert flow.completed
    assert flow_finished == [True]
    assert main.AttackTab.RESULT_REVEAL_INTERVAL_MS >= 55
    app.processEvents()
