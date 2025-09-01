document.addEventListener('DOMContentLoaded', () => {
    const csvUploader = document.getElementById('csv-uploader');
    const dashboardContent = document.getElementById('dashboard-content');

    let allData = [];
    let pieChart = null;
    let barChart = null;

    const periodSelector = document.getElementById('period-selector');
    const totalIncomeEl = document.getElementById('total-income');
    const totalExpenseEl = document.getElementById('total-expense');
    const balanceEl = document.getElementById('balance');
    const majorCategorySelector = document.getElementById('major-category-selector');
    const detailsTableBody = document.querySelector('#details-table tbody');

    csvUploader.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (!file) {
            return;
        }

        Papa.parse(file, {
            header: true,
            skipEmptyLines: true,
            complete: (results) => {
                allData = results.data.filter(row => row['計算対象'] === '1' && row['振替'] === '0')
                                      .map(row => ({
                                          ...row,
                                          '金額（円）': parseInt(row['金額（円）'], 10),
                                          '日付': new Date(row['日付'])
                                      }));
                dashboardContent.style.display = 'block';
                init();
            }
        });
    });

    function init() {
        const periods = ['全期間', ...[...new Set(allData.map(row => row['集計期間']))].sort().reverse()];
        periodSelector.innerHTML = periods.map(p => `<option value="${p}">${p}</option>`).join('');

        periodSelector.addEventListener('change', updateDashboard);
        majorCategorySelector.addEventListener('change', updateDrillDown);

        updateDashboard();
    }

    function updateDashboard() {
        const selectedPeriod = periodSelector.value;
        const filteredData = selectedPeriod === '全期間' 
            ? allData 
            : allData.filter(row => row['集計期間'] === selectedPeriod);

        updateSummary(filteredData);
        updatePieChart(filteredData);
        updateDrillDown(filteredData);
    }

    function updateSummary(data) {
        const income = data.filter(r => r['金額（円）'] > 0).reduce((sum, r) => sum + r['金額（円）'], 0);
        const expense = data.filter(r => r['金額（円）'] < 0).reduce((sum, r) => sum + Math.abs(r['金額（円）']), 0);
        const balance = income - expense;

        totalIncomeEl.textContent = `${income.toLocaleString()} 円`;
        totalExpenseEl.textContent = `${expense.toLocaleString()} 円`;
        balanceEl.textContent = `${balance.toLocaleString()} 円`;
    }

    function updatePieChart(data) {
        const expenses = data.filter(r => r['金額（円）'] < 0);
        const categoryExpenses = expenses.reduce((acc, cur) => {
            const category = cur['大項目'];
            acc[category] = (acc[category] || 0) + Math.abs(cur['金額（円）']);
            return acc;
        }, {});

        const sortedCategories = Object.entries(categoryExpenses).sort(([, a], [, b]) => b - a);
        const labels = sortedCategories.map(([cat]) => cat);
        const values = sortedCategories.map(([, val]) => val);

        if (pieChart) pieChart.destroy();
        pieChart = new Chart(document.getElementById('pie-chart'), {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed !== null) {
                                    label += new Intl.NumberFormat('ja-JP', { style: 'currency', currency: 'JPY' }).format(context.parsed);
                                }
                                return label;
                            }
                        }
                    }
                }
            },
        });
    }

    function updateDrillDown(data) {
        const filteredData = Array.isArray(data) ? data : allData.filter(row => periodSelector.value === '全期間' || row['集計期間'] === periodSelector.value);
        const expenses = filteredData.filter(r => r['金額（円）'] < 0);

        const majorCategories = ['すべてのカテゴリ', ...new Set(expenses.map(r => r['大項目']))];
        const currentMajorCategory = majorCategorySelector.value;
        majorCategorySelector.innerHTML = majorCategories.map(c => `<option value="${c}" ${c === currentMajorCategory ? 'selected' : ''}>${c}</option>`).join('');

        const selectedMajorCategory = majorCategorySelector.value;
        const drillDownData = selectedMajorCategory === 'すべてのカテゴリ'
            ? expenses
            : expenses.filter(r => r['大項目'] === selectedMajorCategory);

        updateBarChart(drillDownData);
        updateDetailsTable(drillDownData);
    }

    function updateBarChart(data) {
        const subCategoryExpenses = data.reduce((acc, cur) => {
            const category = cur['中項目'];
            acc[category] = (acc[category] || 0) + Math.abs(cur['金額（円）']);
            return acc;
        }, {});

        const sortedSubCategories = Object.entries(subCategoryExpenses).sort(([, a], [, b]) => b - a);
        const labels = sortedSubCategories.map(([cat]) => cat);
        const values = sortedSubCategories.map(([, val]) => val);

        if (barChart) barChart.destroy();
        barChart = new Chart(document.getElementById('bar-chart'), {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: '支出',
                    data: values,
                    backgroundColor: 'rgba(54, 162, 235, 0.6)',
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }

    function updateDetailsTable(data) {
        detailsTableBody.innerHTML = '';
        const sortedData = [...data].sort((a, b) => b['日付'] - a['日付']);

        for (const row of sortedData) {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${row['日付'].toLocaleDateString()}</td>
                <td>${row['内容']}</td>
                <td>${Math.abs(row['金額（円）']).toLocaleString()}</td>
                <td>${row['中項目']}</td>
            `;
            detailsTableBody.appendChild(tr);
        }
    }
});
