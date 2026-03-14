-- Put this file in your Wireshark personal plugins directory

local f_time_epoch   = Field.new("frame.time_epoch")
local f_time_delta   = Field.new("frame.time_delta")
local f_frame_len    = Field.new("frame.len")
local f_frame_num    = Field.new("frame.number")

local f_ip_src       = Field.new("ip.src")
local f_ip_dst       = Field.new("ip.dst")
local f_ip_proto     = Field.new("ip.proto")
local f_ip_dscp      = Field.new("ip.dsfield.dscp")
local f_ip_dsfield   = Field.new("ip.dsfield")

local f_tcp_stream   = Field.new("tcp.stream")
local f_tcp_seq      = Field.new("tcp.seq")
local f_tcp_ack      = Field.new("tcp.ack")
local f_tcp_len      = Field.new("tcp.len")
local f_tcp_srcport  = Field.new("tcp.srcport")
local f_tcp_dstport  = Field.new("tcp.dstport")
local f_tcp_window   = Field.new("tcp.window_size")

local f_udp_srcport  = Field.new("udp.srcport")
local f_udp_dstport  = Field.new("udp.dstport")
local f_udp_length   = Field.new("udp.length")

local f_retrans      = Field.new("tcp.analysis.retransmission")
local f_dupack       = Field.new("tcp.analysis.duplicate_ack")
local f_fastret      = Field.new("tcp.analysis.fast_retransmission")
local f_ooo          = Field.new("tcp.analysis.out_of_order")
local f_lostseg      = Field.new("tcp.analysis.lost_segment")
local f_spurious     = Field.new("tcp.analysis.spurious_retransmission")
local f_ackrtt       = Field.new("tcp.analysis.ack_rtt")

local outfile

if package.config:sub(1,1) == "\\" then
    outfile = os.getenv("TEMP") .. "\\ws_export.csv"
else
    outfile = "/tmp/ws_export.csv"
end

local file = nil
local first_time = nil
local last_time = nil

local function csv(v)
    if v == nil then return "" end
    v = tostring(v)
    v = v:gsub('"', '""')
    return '"' .. v .. '"'
end

local function bool01(v)
    if v then return "1" else return "0" end
end

local function human_time(epoch)
    if not epoch then
        return ""
    end

    local t = tonumber(epoch)
    if not t then
        return ""
    end

    local sec = math.floor(t)
    local ms = math.floor((t - sec) * 1000)

    return os.date("%Y-%m-%d %H:%M:%S", sec) .. string.format(".%03d", ms)
end

local function open_file()
    if file then
        file:close()
    end

    file = assert(io.open(outfile, "w"))

    file:write(table.concat({
        "Frame",
        "Time",
        "Delta",
        "Source",
        "Destination",
        "IP Proto",
        "DSCP",
        "DSField",

        "TCP Stream",
        "TCP Seq",
        "TCP Ack",
        "TCP Len",
        "TCP SrcPort",
        "TCP DstPort",
        "TCP Window",

        "UDP SrcPort",
        "UDP DstPort",
        "UDP Length",

        "Length",

        "Retrans",
        "DupAck",
        "FastRetrans",
        "OutOfOrder",
        "LostSegment",
        "SpuriousRetrans",
        "AckRTT"
    }, ",") .. "\n")
end

open_file()

local tap = Listener.new("frame", "tcp or udp")

function tap.packet(pinfo, tvb)
    local time_epoch = f_time_epoch()

    if time_epoch then
        local t = tonumber(tostring(time_epoch))
        if t then
            if not first_time then
                first_time = t
            end
            last_time = t
        end
    end

    local frame       = f_frame_num()
    local time_delta  = f_time_delta()
    local frame_len   = f_frame_len()

    local ip_src      = f_ip_src()
    local ip_dst      = f_ip_dst()
    local ip_proto    = f_ip_proto()
    local ip_dscp     = f_ip_dscp()
    local ip_dsfield  = f_ip_dsfield()

    local tcp_stream  = f_tcp_stream()
    local tcp_seq     = f_tcp_seq()
    local tcp_ack     = f_tcp_ack()
    local tcp_len     = f_tcp_len()
    local tcp_srcport = f_tcp_srcport()
    local tcp_dstport = f_tcp_dstport()
    local tcp_window  = f_tcp_window()

    local udp_srcport = f_udp_srcport()
    local udp_dstport = f_udp_dstport()
    local udp_length  = f_udp_length()

    local retrans     = bool01(f_retrans())
    local dupack      = bool01(f_dupack())
    local fastret     = bool01(f_fastret())
    local ooo         = bool01(f_ooo())
    local lostseg     = bool01(f_lostseg())
    local spurious    = bool01(f_spurious())
    local ackrtt      = f_ackrtt()

    file:write(table.concat({
        csv(frame),
        csv(time_epoch),
        csv(time_delta),
        csv(ip_src),
        csv(ip_dst),
        csv(ip_proto),
        csv(ip_dscp),
        csv(ip_dsfield),

        csv(tcp_stream),
        csv(tcp_seq),
        csv(tcp_ack),
        csv(tcp_len),
        csv(tcp_srcport),
        csv(tcp_dstport),
        csv(tcp_window),

        csv(udp_srcport),
        csv(udp_dstport),
        csv(udp_length),

        csv(frame_len),

        csv(retrans),
        csv(dupack),
        csv(fastret),
        csv(ooo),
        csv(lostseg),
        csv(spurious),
        csv(ackrtt)
    }, ",") .. "\n")
end

function tap.draw()
    if file then
        file:write("# capture_start=" .. human_time(first_time) .. "\n")
        file:write("# capture_end=" .. human_time(last_time) .. "\n")
        file:flush()
    end
end