# coding: utf-8

require("net/http")
require("openssl")
require("uri")
require("json")

def get(url, header=nil, limit=10)
    url = URI.parse(url)
    http = Net::HTTP.new(url.host, url.port)
    http.use_ssl = true
    # Just for test
    http.verify_mode = OpenSSL::SSL::VERIFY_NONE
    res = http.start do |h|
        req = Net::HTTP::Get.new(url.request_uri, header)
        h.request(req)
    end

    if res.kind_of?(Net::HTTPRedirection) && limit > 0
        get(res["location"], header, limit - 1)
    else
        res
    end
end

def download(exe_name, url)
    puts "Getting latest release information..."
    res = get(url)
    latest_release_info = JSON.parse(res.body)

    puts "Finding #{exe_name}..."
    exe_url = latest_release_info["assets"].find{ |i| i["name"] == exe_name }["browser_download_url"]

    puts "Downloading #{exe_name}..."
    res = get(exe_url, { "Accept" => "application/octet-stream" })
    File.binwrite(exe_name, res.body.b)
end

def main_python(python_exe_name)
    download(python_exe_name, "https://api.github.com/repos/masamitsu-murase/single_binary_stackless_python/releases/latest")
end

def main_libclang(libclang_dll_name)
    download(libclang_dll_name, "https://api.github.com/repos/masamitsu-murase/clang/releases/latest")
end

case ARGV[0]
when "python"
    main_python(ARGV[1])
when "libclang"
    main_libclang(ARGV[1])
else
    raise "Unknown target: #{ARGV[0]}"
end
