// static/admin/js/prize_distribution_widget.js

document.addEventListener('DOMContentLoaded', function() {
    const widget = document.getElementById('prize-distribution-widget');
    if (!widget) return;

    const prizeEntriesContainer = widget.querySelector('#prize-entries');
    const addEntryButton = widget.querySelector('#add-prize-entry');
    const hiddenInput = widget.querySelector(`input[name="${widget.dataset.fieldName}"]`);

    function updateHiddenInput() {
        const entries = prizeEntriesContainer.querySelectorAll('.prize-entry');
        const data = {};
        let isValid = true;

        entries.forEach(entry => {
            const rankInput = entry.querySelector('.prize-rank');
            const amountInput = entry.querySelector('.prize-amount');
            const rank = rankInput.value.trim();
            const amount = amountInput.value.trim();

            if (rank && amount) {
                if (data[rank]) {
                    rankInput.style.borderColor = 'red';
                    isValid = false;
                } else {
                    rankInput.style.borderColor = '';
                    data[rank] = parseFloat(amount);
                }
            }
        });
        
        if (isValid) {
            hiddenInput.value = JSON.stringify(data);
        }
    }

    function createPrizeEntry(rank = '', amount = '') {
        const entryDiv = document.createElement('div');
        entryDiv.classList.add('prize-entry');

        const rankInput = document.createElement('input');
        rankInput.type = 'number';
        rankInput.classList.add('prize-rank');
        rankInput.placeholder = 'Rank';
        rankInput.value = rank;

        const amountInput = document.createElement('input');
        amountInput.type = 'number';
        amountInput.classList.add('prize-amount');
        amountInput.placeholder = 'Amount';
        amountInput.value = amount;

        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.classList.add('remove-prize-entry', 'button');
        removeButton.textContent = '-';

        entryDiv.appendChild(rankInput);
        entryDiv.appendChild(amountInput);
        entryDiv.appendChild(removeButton);

        return entryDiv;
    }

    // Event delegation for remove buttons
    prizeEntriesContainer.addEventListener('click', function(e) {
        if (e.target.classList.contains('remove-prize-entry')) {
            e.target.closest('.prize-entry').remove();
            updateHiddenInput();
        }
    });

    // Event delegation for input changes
    prizeEntriesContainer.addEventListener('input', function(e) {
        if (e.target.classList.contains('prize-rank') || e.target.classList.contains('prize-amount')) {
            updateHiddenInput();
        }
    });

    addEntryButton.addEventListener('click', function() {
        prizeEntriesContainer.appendChild(createPrizeEntry());
    });

    // Initial load
    if (hiddenInput.value) {
        try {
            const initialData = JSON.parse(hiddenInput.value);
            prizeEntriesContainer.innerHTML = ''; // Clear existing
            if (Object.keys(initialData).length > 0) {
                for (const [rank, amount] of Object.entries(initialData)) {
                    prizeEntriesContainer.appendChild(createPrizeEntry(rank, amount));
                }
            } else {
                prizeEntriesContainer.appendChild(createPrizeEntry());
            }
        } catch (e) {
            console.error('Error parsing prize distribution JSON:', e);
            prizeEntriesContainer.innerHTML = '';
            prizeEntriesContainer.appendChild(createPrizeEntry());
        }
    } else {
         prizeEntriesContainer.innerHTML = '';
         prizeEntriesContainer.appendChild(createPrizeEntry());
    }
});
