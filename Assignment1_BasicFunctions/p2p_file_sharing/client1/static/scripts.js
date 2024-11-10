function signIn() {
    const peerId = document.getElementById("peerIdInput").value;
    
    if (!peerId) {
        alert("Please enter a peer ID.");
        return;
    }

    fetch("/sign_in", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ peer_id: peerId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === "success") {
            alert(`Signed in with peer ID: ${peerId}\nIP: ${data.ip}\nPort: ${data.port}`);
        } else {
            alert(`Error: ${data.error}`);
        }
    })
    .catch(error => {
        console.error("Error:", error);
        alert("An error occurred during sign in.");
    });
}

function signOut() {
    fetch("/sign_out", {
        method: "POST",
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
        } else {
            alert(data.message);
        }
    })
    .catch(error => {
        console.error("Error:", error);
    });
    const dis = document.getElementById("discover-section");
    dis.style.display = 'none';

    const file = document.getElementById("file-list");
    file.style.display = 'none';

    // Xóa toàn bộ các <li> trong phần file-list
    const fileList = document.getElementById('fileList');
    fileList.innerHTML = '';  // Xóa tất cả các file trong danh sách

    // Xóa toàn bộ các dòng trong bảng discover
    const discoverTableBody = document.getElementById('discoverTable').querySelector('tbody');
    discoverTableBody.innerHTML = '';  // Xóa tất cả các dòng trong bảng
}

function updateFileList() {
    fetch("/publish")
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            const fileList = document.getElementById('fileList');
            fileList.innerHTML = '';
            data.files.forEach(file => {
                const listItem = document.createElement('li');
                listItem.textContent = file;
                fileList.appendChild(listItem);
            });
            document.getElementById('file-list').style.display = 'block';
        });
}

function updateDiscoverTable() {
    fetch("/discover")
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
                return;
            }
            const tableBody = document.getElementById('discoverTable').querySelector('tbody');
            tableBody.innerHTML = '';
            data.clients.forEach(client => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${client.peer_id}</td>
                    <td>${client.ip}</td>
                    <td>${client.port}</td>
                    <td>${client.files.join(', ')}</td>
                `;
                tableBody.appendChild(row);
            });
            document.getElementById('discover-section').style.display = 'block';
        });
}
function pingTracker() {
    const startTime = performance.now();

    fetch("/ping")
        .then(response => response.json())
        .then(data => {
            if (data.ping !== undefined) {
                const endTime = performance.now();
                const pingTime = Math.round(endTime - startTime);  // Tính thời gian ping
                alert(`Ping response time: ${pingTime} ms`);
            } else {
                alert("Ping failed: " + data.error);
            }
        })
        .catch(error => {
            console.error("Error:", error);
            alert("An error occurred while pinging the server.");
        });
}
function fetchFile() {
    const filename = document.getElementById('fetch-filename').value;
    if (!filename) {
        alert("Please enter a filename.");
        return;
    }
    
    fetch("/fetch", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ filename: filename })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
        } else {
            alert(data.message);
        }
    })
    .catch(error => {
        console.error("Error:", error);
    });
}
function publishFiles() {
    showSection('file-list');  // Hiển thị phần file-list

    // Cập nhật danh sách file từ server (nếu cần)
    updateFileList();
}
function discoverPeers() {
    // Gọi API hoặc thực hiện chức năng Discover
    showSection('discover-section');  // Hiển thị phần discover-section

    // Cập nhật bảng Discover từ server (nếu cần)
    updateDiscoverTable();
}
function showSection(sectionId) {
    // Ẩn tất cả các section
    document.getElementById('file-list').style.display = 'none';
    document.getElementById('discover-section').style.display = 'none';

    // Hiển thị section được chọn
    document.getElementById(sectionId).style.display = 'block';
}