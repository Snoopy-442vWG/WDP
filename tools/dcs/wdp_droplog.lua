--[[ ==================================================================================================================
  WDP drop logger -- records weapon releases and impacts to dcs.log for calibrating WDP.

  HOW TO USE
    1. Mission Editor: add a trigger  ONCE  /  TIME MORE (1)  /  DO SCRIPT FILE  ->  wdp_droplog.lua
    2. Fly the test drops.
    3. Quit DCS, then send:  Saved Games\DCS\Logs\dcs.log   (or Saved Games\DCS.openbeta\Logs\dcs.log)

  Every line this script writes starts with "WDP," so it is easy to pull out of the log.
  Units are SI from the sim: metres, m/s, kelvin, pascals. DCS world frame: x = north, z = east, y = up.

  Line types
    WDP,HDR,...            column headers (written once at start)
    WDP,REL,...            aircraft + weapon state at the instant of release
    WDP,TRK,...            weapon position samples every 0.5 s (used to fit drag)
    WDP,IMP,...            weapon impact point (last sample, extrapolated to the terrain)
================================================================================================================== ]]

WDP = WDP or {}
WDP.sampleDt   = 0.02     -- s between weapon position checks (impact accuracy)
WDP.trackEvery = 0.5      -- s between TRK lines written to the log
WDP.shotCount  = 0

local function f(v, n) return string.format("%." .. (n or 2) .. "f", v or 0) end

local function log(s) env.info("WDP," .. s) end

local function vlen(v) return math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z) end

local function dot(a, b) return a.x * b.x + a.y * b.y + a.z * b.z end

-- angle (deg) of a vector above the horizon (negative = descending)
local function elev(v)
    local h = math.sqrt(v.x * v.x + v.z * v.z)
    return math.deg(math.atan2(v.y, h))
end

-- heading (deg true, DCS map frame) of a vector
local function hdg(v)
    local h = math.deg(math.atan2(v.z, v.x))
    if h < 0 then h = h + 360 end
    return h
end

local function groundHeight(p)
    return land.getHeight({ x = p.x, y = p.z })
end

local function writeHeaders()
    log("HDR,REL,shot,t,pilot,aircraft,weapon,x,y,z,lat,lon,alt_msl,gnd_elev,vx,vy,vz,tas_air,gs,fpa_deg,trk_deg," ..
        "pitch_deg,roll_deg,hdg_deg,aoa_deg,nz,temp_k,press_pa,wind_x,wind_z,wvx,wvy,wvz,mass_kg")
    log("HDR,TRK,shot,t,x,y,z,vx,vy,vz")
    log("HDR,IMP,shot,t,tof,x,y,z,lat,lon,gnd_elev,range_m,cross_m,last_vx,last_vy,last_vz")
end

-- track a released weapon until it stops existing; write impact
local function trackWeapon(args, time)
    local w = args.weapon
    if w and w:isExist() then
        local p, v = w:getPoint(), w:getVelocity()
        args.last = { p = p, v = v, t = time }
        if time - args.lastTrk >= WDP.trackEvery then
            args.lastTrk = time
            log(table.concat({ "TRK", args.shot, f(time, 3), f(p.x), f(p.y), f(p.z), f(v.x), f(v.y), f(v.z) }, ","))
        end
        return time + WDP.sampleDt
    end
    -- weapon gone: extrapolate last sample down to the terrain
    local L = args.last
    if not L then return nil end
    local p, v = L.p, L.v
    local dtGuess = 0
    for _ = 1, 20 do
        local gx, gy, gz = p.x + v.x * dtGuess, p.y + v.y * dtGuess - 4.905 * dtGuess * dtGuess, p.z + v.z * dtGuess
        local gh = land.getHeight({ x = gx, y = gz })
        local above = gy - gh
        if math.abs(above) < 0.05 then break end
        local vy = v.y - 9.81 * dtGuess
        if vy >= -1 then break end
        dtGuess = dtGuess + above / -vy
        if dtGuess < 0 then dtGuess = 0 break end
        if dtGuess > WDP.sampleDt * 3 then dtGuess = WDP.sampleDt * 3 break end
    end
    local ix, iz = p.x + v.x * dtGuess, p.z + v.z * dtGuess
    local ih = land.getHeight({ x = ix, y = iz })
    local imp = { x = ix, y = ih, z = iz }
    local lat, lon = coord.LOtoLL(imp)
    -- along-track / cross-track distance from release point, using release ground track
    local dx, dz = ix - args.rel.x, iz - args.rel.z
    local th = math.rad(args.trk)
    local along = dx * math.cos(th) + dz * math.sin(th)
    local cross = -dx * math.sin(th) + dz * math.cos(th)
    local tImp = L.t + dtGuess
    log(table.concat({ "IMP", args.shot, f(tImp, 3), f(tImp - args.t0, 3), f(ix), f(ih), f(iz), f(lat, 6), f(lon, 6),
        f(ih), f(along), f(cross), f(v.x), f(v.y), f(v.z) }, ","))
    return nil
end

local handler = {}
function handler:onEvent(e)
    if e.id ~= world.event.S_EVENT_SHOT or not e.weapon or not e.initiator then return end
    local ok, err = pcall(function()
        local u, w = e.initiator, e.weapon
        local t = timer.getTime()
        WDP.shotCount = WDP.shotCount + 1
        local shot = WDP.shotCount

        local pos = u:getPosition()          -- p = point, x = nose, y = up, z = right (unit vectors)
        local p = pos.p
        local v = u:getVelocity()            -- ground-referenced velocity
        local wind = atmosphere.getWind(p)   -- air-mass velocity (x, y, z)
        local va = { x = v.x - wind.x, y = v.y - wind.y, z = v.z - wind.z }   -- air-relative velocity
        local tas = vlen(va)
        local gs = math.sqrt(v.x * v.x + v.z * v.z)

        -- attitude from body axes
        local pitch = math.deg(math.asin(math.max(-1, math.min(1, pos.x.y))))
        local roll = math.deg(math.atan2(-pos.z.y, pos.y.y))
        local heading = hdg(pos.x)
        -- angle of attack: air velocity projected on the body x-y plane, angle from the nose
        local aoa = math.deg(math.atan2(-dot(va, pos.y), dot(va, pos.x)))

        local temp, press = atmosphere.getTemperatureAndPressure(p)
        local lat, lon, alt = coord.LOtoLL(p)
        local wp, wv = w:getPoint(), w:getVelocity()
        local desc = w:getDesc() or {}
        local acName = u.getTypeName and u:getTypeName() or "?"
        local pilot = (u.getPlayerName and u:getPlayerName()) or (u.getName and u:getName()) or "?"

        -- load factor not exposed directly: logged as 0 (computed offline from the TRK of the aircraft if needed)
        log(table.concat({ "REL", shot, f(t, 3), pilot, acName, w:getTypeName(),
            f(p.x), f(p.y), f(p.z), f(lat, 6), f(lon, 6), f(p.y), f(groundHeight(p)),
            f(v.x), f(v.y), f(v.z), f(tas), f(gs), f(elev(va), 3), f(hdg(v)),
            f(pitch, 3), f(roll, 2), f(heading, 2), f(aoa, 3), "0",
            f(temp, 2), f(press, 0), f(wind.x), f(wind.z), f(wv.x), f(wv.y), f(wv.z), f(desc.mass or 0, 1) }, ","))

        timer.scheduleFunction(trackWeapon,
            { weapon = w, shot = shot, t0 = t, lastTrk = t, rel = p, trk = hdg(v), last = { p = wp, v = wv, t = t } },
            t + WDP.sampleDt)
    end)
    if not ok then env.info("WDP,ERR," .. tostring(err)) end
end

world.addEventHandler(handler)
writeHeaders()
trigger.action.outText("WDP drop logger running -- releases/impacts are written to dcs.log", 10)
env.info("WDP,START,WDP drop logger v1")
